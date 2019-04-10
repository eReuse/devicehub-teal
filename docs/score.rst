**************
SCORE v2
**************

Introduction
*************

The first iteration consists on making an exhaustive list of variables that impact on computers and their components, smartphones, tablets, printers, and computer monitors.
Variables have to be realistically measurable and have a significant impact.

List of sources where can extract device information:

    • *eReuse softwares*:
        ◦ WC: Workbench Computer

        ◦ WM: Workbench Mobile

        ◦ App: Android App (through Scan)

        ◦ Web: Web (manually written in a form)

We define 5 categories to measure:

    • Functionality (F). Answers to “does the machine work well?” Condition tests fall in here.
    • Appearance (A). Aesthetic evaluation, surface deterioration.
    • Performance (Q). How good is the machine, in terms of performance. Benchmarks, power, and characteristics fall here. The quality score, that represents the performance of the device, the functionality score, that based on the correct working of the buttons, audio and connectivity aspects, and the appaerance score, that focused  on the aesthetics and cosmetics aspects like visual damage on screen, buttons or cabinet.
    • Market value (MV). Perceived value, brand recognition, selling value.
    • Cost of repair, refurbish and manufacture. ( C )

List of source where can input information of rating a device:

    1. When processing the device with Workbench Computer or WB Mobile.
    2. Using the Android App (through Scan).
    3. ...
    4. Anytime after manually written in a form in the website.

There are three types of rating a device, depend on the aspect you are focusing on:

    1. `Quality Rate`
    2. `Functionality Rate`
    3. `Appearance Rate`
    4. `Final Rate`
        1. ComputerRate
        2. MobileRate
        3. ManualRate
To structure device events information, create two different main class Benchmark and Test.
Benchmark class is part of the **quality rate** and Test class is part of the **functionality rate**.

Rate Aspects
*************

The following will explain in more detail the three types of rate. Rate class is where store all algorithm results.

**1. Quality Rate**

    Device components immutable characteristics and Benchmark, the act of gauging the performance of a device.

**2. Functionality Rate**

    Test, the act of testing usage condition of a device and its functionality aspects/characteristics. Following standard R2 specification*.

**3. Appearance Rate**

    Mainly is compute using the results of a visual Test, it is a test of appearance that its aspects are represented with grade.
    It focuses mainly on the aesthetic or cosmetic defects of important parts of the device, such as the chassis, display (screen) and cameras.


Below is explained in more detail how the calculations and formulas that are used to compute the score of a device.


**Algorithm**
****************

Explication of how to compute score of a device, step by step:

    1. Normalization the components characteristics.
    Normalized the characteristics of the components between 0 and 1 using the theoretical norms table**
    with xMin and xMax and standardize the values applying the following formula:

    **Normalization characteristic value = (x −xMin)/(xMax −xMin)**

    2. Merge the characteristics of every component in one score.
    Carry out the harmonic mean weighted by the weight of each characteristic.

    **Harmonic Mean = sum(char_weights)/(sum(char_weight[i]/char_value[i])**

    Note: sum(char_weights) = 1

    3. Merge the components individual rates into a single score device. Again, we calculate the weighted harmonic mean.
    We establish all the components weights, for example; 20% for processor, 10% for data storage, 40% for RAM,
    15% for display, 15 % for battery. The result is a unique performance score (Quality rate).

    4. Grouping all categories aspects of a device in unique final rate. Sum all rate types:

    **Final Rate = Quality Rate + Functionality Rate + Appearance Rate**

Extra information
*******************

**Standard R2 Testing**

Elements of effective testing include the following:

    • Test should include results for specific functions, not combined grade or letter grade

    • Test should be “Pass / Fail”

    • “Fail” test should include failure reason

    • Test results must be recorded and stored in and ordered system

    • Test results must be retained after unit shipment or sale.



**Example of Theorical Normals**

Characteristics xMin	xMax	xMax-xMin

- Display Size	3,5	7,24	3,74

- Processor Cores	1	6	5

- Processor Speed	1,4	3,4	2

- RAM Size	512	16384	15872

- RAM Speed	133	1333	1200

- Data Storage Size	4096	262144	258048

- Data Storage Read Speed	2,7	109,5	106,8

- Data Storage Write Speed	2	27,35	25,35

- Battery Capacity	2200	6000	3800

- Camera Resolution	8	64	56

