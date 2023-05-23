import subprocess
from contextlib import suppress
from typing import Any, Set

from ereuse_devicehub.ereuse_utils import text


def run(
    *cmd: Any,
    out=subprocess.PIPE,
    err=subprocess.DEVNULL,
    to_string=True,
    check=True,
    shell=False,
    **kwargs,
) -> subprocess.CompletedProcess:
    """subprocess.run with a better API.

    :param cmd: A list of commands to execute as parameters.
                Parameters will be passed-in to ``str()`` so they
                can be any object that can handle str().
    :param out: As ``subprocess.run.stdout``.
    :param err: As ``subprocess.run.stderr``.
    :param to_string: As ``subprocess.run.universal_newlines``.
    :param check: As ``subprocess.run.check``.
    :param shell:
    :param kwargs: Any other parameters that ``subprocess.run``
                   accepts.
    :return: The result of executing ``subprocess.run``.
    """
    cmds = tuple(str(c) for c in cmd)
    return subprocess.run(
        ' '.join(cmds) if shell else cmds,
        stdout=out,
        stderr=err,
        universal_newlines=to_string,
        check=check,
        shell=shell,
        **kwargs,
    )


class ProgressiveCmd:
    """Executes a cmd while interpreting its completion percentage.

    The completion percentage of the cmd is stored in
    :attr:`.percentage` and the user can obtain percentage
    increments by executing :meth:`.increment`.

    This class is useful to use within a child thread, so a main
    thread can request from time to time the percentage / increment
    status of the running command.
    """

    READ_LINE = None
    DECIMALS = {4, 5, 6}
    DECIMAL_NUMBERS = 2
    INT = {1, 2, 3}

    def __init__(
        self,
        *cmd: Any,
        stdout=subprocess.DEVNULL,
        number_chars: Set[int] = INT,
        decimal_numbers: int = None,
        read: int = READ_LINE,
        callback=None,
        check=True,
    ):
        """
        :param cmd: The command to execute.
        :param stderr: the stderr passed-in to Popen.
        :param stdout: the stdout passed-in to Popen
        :param number_chars: The number of chars used to represent
                             the percentage. Normalized cases are
                             :attr:`.DECIMALS` and :attr:`.INT`.
        :param read: For commands that do not print lines, how many
                     characters we should read between updates.
                     The percentage should be between those
                     characters.
        :param callback: If passed in, this method is executed every time
                         run gets an update from the command, passing
                         in the increment from the last execution.
                         If not passed-in, you can get such increment
                         by executing manually the ``increment`` method.
        :param check: Raise error if subprocess return code is non-zero.
        """
        self.cmd = tuple(str(c) for c in cmd)
        self.read = read
        self.step = 0
        self.check = check
        self.number_chars = number_chars
        self.decimal_numbers = decimal_numbers
        # We call subprocess in the main thread so the main thread
        # can react on ``CalledProcessError`` exceptions
        self.conn = conn = subprocess.Popen(
            self.cmd, universal_newlines=True, stderr=subprocess.PIPE, stdout=stdout
        )
        self.out = conn.stdout if stdout == subprocess.PIPE else conn.stderr
        self._callback = callback
        self.last_update_percentage = 0
        self.percentage = 0

    @property
    def percentage(self):
        return self._percentage

    @percentage.setter
    def percentage(self, v):
        self._percentage = v
        if self._callback and self._percentage > 0:
            increment = self.increment()
            if (
                increment > 0
            ):  # Do not bother calling if there has not been any increment
                self._callback(increment, self._percentage)

    def run(self) -> None:
        """Processes the output."""
        while True:
            out = self.out.read(self.read) if self.read else self.out.readline()
            if out:
                with suppress(StopIteration):
                    self.percentage = next(
                        text.positive_percentages(
                            out, self.number_chars, self.decimal_numbers
                        )
                    )
            else:  # No more output
                break
        return_code = self.conn.wait()  # wait until cmd ends
        if self.check and return_code != 0:
            raise subprocess.CalledProcessError(
                self.conn.returncode, self.conn.args, stderr=self.conn.stderr.read()
            )

    def increment(self):
        """Returns the increment of progression from
        the last time this method is executed.
        """
        # for cmd badblocks the increment can be negative at the
        # beginning of the second step where last_percentage
        # is 100 and percentage is 0. By using max we
        # kind-of reset the increment and start counting for
        # the second step
        increment = max(self.percentage - self.last_update_percentage, 0)
        self.last_update_percentage = self.percentage
        return increment
