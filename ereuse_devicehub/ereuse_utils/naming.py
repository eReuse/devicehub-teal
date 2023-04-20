from inflection import (
    camelize,
    dasherize,
    parameterize,
    pluralize,
    singularize,
    underscore,
)

HID_CONVERSION_DOC = """
        The HID is the result of concatenating,
        in the following order: the type of device (ex. Computer),
        the manufacturer name, the model name, and the S/N. It is joined
        with hyphens, and adapted to comply with the URI specification, so
        it can be used in the URI identifying the device on the Internet.
        The conversion is done as follows:
    
        1. non-ASCII characters are converted to their ASCII equivalent or
           removed.
        2. Characterst that are not letters or numbers are converted to 
           underscores, in a way that there are no trailing underscores
           and no underscores together, and they are set to lowercase.
        
        Ex. ``laptop-acer-aod270-lusga_0d0242201212c7614``
    """


class Naming:
    """
    In DeviceHub there are many ways to name the same resource (yay!), this is because of all the different
    types of schemas we work with. But no worries, we offer easy ways to change between naming conventions.

    - TypeCase (or resource-type) is the one represented with '@type' and follow PascalCase and always singular.
        This is the standard preferred one.
    - resource-case is the eve naming, using the standard URI conventions. This one is tricky, as although the types
        are represented in singular, the URI convention is to be plural (Event vs events), however just few of them
        follow this rule (Snapshot [type] to snapshot [resource]). You can set which ones you want to change their
        number.
    - python_case is the one used by python for its folders and modules. It is underscored and always singular.
    """

    TYPE_PREFIX = ':'
    RESOURCE_PREFIX = '_'

    @staticmethod
    def resource(string: str):
        """
        :param string: String can be type, resource or python case
        """
        try:
            prefix, resulting_type = Naming.pop_prefix(string)
            prefix += Naming.RESOURCE_PREFIX
        except IndexError:
            prefix = ''
            resulting_type = string
        resulting_type = dasherize(underscore(resulting_type))
        return prefix + pluralize(resulting_type)

    @staticmethod
    def python(string: str):
        """
        :param string: String can be type, resource or python case
        """
        return underscore(singularize(string))

    @staticmethod
    def type(string: str):
        try:
            prefix, resulting_type = Naming.pop_prefix(string)
            prefix += Naming.TYPE_PREFIX
        except IndexError:
            prefix = ''
            resulting_type = string
        resulting_type = singularize(resulting_type)
        resulting_type = resulting_type.replace(
            '-', '_'
        )  # camelize does not convert '-' but '_'
        return prefix + camelize(resulting_type)

    @staticmethod
    def url_word(word: str):
        """
        Normalizes a full word to be inserted to an url. If the word has spaces, etc, is used '_' and not '-'
        """
        return parameterize(word, '_')

    @staticmethod
    def pop_prefix(string: str):
        """Erases the prefix and returns it.
        :throws IndexError: There is no prefix.
        :return A set with two elements: 1- the prefix, 2- the type without it.
        """
        result = string.split(Naming.TYPE_PREFIX)
        if len(result) == 1:
            result = string.split(Naming.RESOURCE_PREFIX)
            if len(result) == 1:
                raise IndexError()
        return result

    @staticmethod
    def new_type(type_name: str, prefix: str or None = None) -> str:
        """
        Creates a resource type with optionally a prefix.

        Using the rules of JSON-LD, we use prefixes to disambiguate between different types with the same name:
        one can Accept a device or a project. In eReuse.org there are different events with the same names, in
        linked-data terms they have different URI. In eReuse.org, we solve this with the following:

            "@type": "devices:Accept" // the URI for these events is 'devices/events/accept'
            "@type": "projects:Accept"  // the URI for these events is 'projects/events/accept
            ...

        Type is only used in events, when there are ambiguities. The rest of

            "@type": "devices:Accept"
            "@type": "Accept"

        But these not:

            "@type": "projects:Accept"  // it is an event from a project
            "@type": "Accept"  // it is an event from a device
        """
        if Naming.TYPE_PREFIX in type_name:
            raise TypeError(
                'Cannot create new type: type {} is already prefixed.'.format(type_name)
            )
        prefix = (prefix + Naming.TYPE_PREFIX) if prefix is not None else ''
        return prefix + type_name

    @staticmethod
    def hid(type: str, manufacturer: str, model: str, serial_number: str) -> str:
        (
            """Computes the HID for the given properties of a device.
        The HID is suitable to use to an URI.
        """
            + HID_CONVERSION_DOC
        )
        return '{type}-{mn}-{ml}-{sn}'.format(
            type=Naming.url_word(type),
            mn=Naming.url_word(manufacturer),
            ml=Naming.url_word(model),
            sn=Naming.url_word(serial_number),
        )
