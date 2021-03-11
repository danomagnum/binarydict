import struct
from collections import OrderedDict


class StructObject(object):
    """
    Complex data such as arrays and nested structs need to have a little wits about them.  This object is the
    template for classes that provide those wits.
    """

    def __init__(self):
        """
        Needs to define the format and instantiate the struct
        """
        self.format = ''
        self.endianness = ''
        self.struct = struct.Struct(self.format)


    def __len__(self):
        return self.struct.size

    def set_endianness(self, endianness):
        self.struct = struct.Struct(self.endianness + self.format)

    def parse_unpacked(self, unpacked_data):
        """
        hopefully I can make this unpack generic enough to use for other things than arrays at some point
        :param unpacked_data: a python list of the unpacked elements
        :return: (value, number of items used from list)
        """

        return 0, 0

    def create_packlist(self, value):
        """
        :return: Returns a list that gets combined onto the end of the current list to be packed.
         It should match the format
        """
        return []

    def pack(self, value):
        """
        Takes a dictionary (dict_input)
        and a OrderedDict as described at the top of the file
        and an opitonal offset and then return a regular (non-Ordered) dictionary
        with the data assigned to the keys.
        """
        data_list = self.create_packlist(value)
        return self.struct.pack(*data_list)

    def unpack(self, data_array, offset=0):
        """
        Take raw response data which should be an iterable byte structure,
        and then return an ordered dictionary with the data assigned to the keys.
        """
        unpacked = self.struct.unpack_from(data_array, offset)

        return self.parse_unpacked(unpacked)[0]


class BasicType(StructObject):
    def __init__(self, format_str):
        self.format = format_str
        self.struct = struct.Struct(self.format)

    def parse_unpacked(self, unpacked_data):
        """
        hopefully I can make this unpack generic enough to use for other things than arrays at some point
        :param unpacked_data: a python list of the unpacked elements
        :return: (value, number of items used from list)
        """

        return unpacked_data[0], 1

    def create_packlist(self, value):
        """
        :return: Returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
        """
        return [value]

    def __reduce__(self):
        return (self.__class__, (self.format,))


# Provide easier to use definitions of the constants the struct module uses.
# See https://docs.python.org/3/library/struct.html
CHAR = BasicType('c')
SINT8 = BasicType('b')
UINT8 = BasicType('B')
BOOL = BasicType('?')
SINT16 = BasicType('h')
UINT16 = BasicType('H')
SINT32 = BasicType('l')
UINT32 = BasicType('L')
SINT64 = BasicType('q')
UINT64 = BasicType('Q')
SINT_NATIVE = BasicType('n')
UINT_NATIVE = BasicType('N')
HALF = BasicType('e')
FLOAT = BasicType('f')
DOUBLE = BasicType('d')


class BYTES(StructObject):
    def __init__(self, length):
        """
        Structure object for creating strings that correspond to python byte objects bytes (no encodings)
        :param length: how many elements the array contains
        """
        self.length = length
        self.format = f'{length}s'
        self.struct = struct.Struct(self.format)

    def __reduce__(self):
        return (self.__class__, (self.length,))

    def parse_unpacked(self, unpacked_data):
        """
        hopefully I can make this unpack generic enough to use for other things than arrays at some point
        :param unpacked_data: a python list of the unpacked elements
        :return: (value, number of items used from list)
        """

        str_data = unpacked_data[0]

        return str_data, 1

    def create_packlist(self, value):
        """
        :return: Returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
        """
        return [value]

    def null(self):
        """
        :return: a null byte array as long as this structure
        """
        return bytes([0] * len(self))


class STRING(StructObject):
    def __init__(self, length, null_term=True, encoding=None):
        """
        Structure object for creating strings.  These map to python strings
        :param length: how many elements the array contains
        :param null_term: whether the returned string should end at the first null byte
        :param encoding: what encoding to use when converting to a string and back
        """
        self.length = length
        self.encoding = encoding
        self.null_term = null_term
        self.format = f'{length}s'
        self.struct = struct.Struct(self.format)

    def __reduce__(self):
        return (self.__class__, (self.length, self.null_term, self.encoding))


    def parse_unpacked(self, unpacked_data):
        """
        hopefully I can make this unpack generic enough to use for other things than arrays at some point
        :param unpacked_data: a python list of the unpacked elements
        :return: (value, number of items used from list)
        """

        if self.encoding is None:
            str_data = unpacked_data[0].decode()
        else:
            str_data = unpacked_data[0].decode(encoding=self.encoding)

        if self.null_term:
            str_data = str_data[:str_data.find('\x00')]

        return str_data, 1

    def create_packlist(self, value):
        """
        :return: Returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
        """
        if self.encoding is not None:
            return [value.encode(encoding=self.encoding)]
        else:
            return [value.encode()]


class SPARE(StructObject):
    """
    This StructObject provides a way to add "padding" bytes to your structure.
    """

    def __init__(self, length):
        '''

        :param length: how many bytes of padding to use
        '''
        self.length = length
        self.format = f'{self.length}x'
        self.struct = struct.Struct(self.format)

    def __reduce__(self):
        return (self.__class__, (self.length,))

    def parse_unpacked(self, unpacked_data):
        """
        Because this is a padding value, we will return that we took 0 elements off the unpack_data list.
        and we'll return None as our value
        :param unpacked_data: a python list of the unpacked elements
        :return: value, number of items used from list
        """
        return None, 0

    def create_packlist(self, value):
        """
        in this case we return nothing because this is padding and no values need to end up converted
        to bytes
        :return: returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
        """
        return []


PADDING = SPARE  # alias


class ARRAY(StructObject):
    def __init__(self, data_type, length):
        """
        Structure object for creating arrays.  These map to python lists
        :param data_type: a StructObject instance
        :param length: how many elements the array contains
        """
        self.data_type = data_type
        self.length = length
        self.format = self.data_type.format * self.length
        self.struct = struct.Struct(self.format)

    def __reduce__(self):
        return (self.__class__, (self.data_type, self.length))

    def parse_unpacked(self, unpacked_data):
        """
        In the case of the array we will take the first <self.length> items from the unpacked data list
        and let the caller know that's how many we needed
        :param unpacked_data: a python list of the unpacked elements
        :return: value, number of items used from list
        """

        item_count = 0
        value_list = []
        for i in range(self.length):
            new_value, new_count = self.data_type.parse_unpacked(unpacked_data[item_count:])
            item_count += new_count
            value_list.append(new_value)
        return value_list, item_count

    def create_packlist(self, value):
        """
        :return:
         returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
         In this case value should be a listlike object
        """
        packlist = []
        for i in range(self.length):
            new_list = self.data_type.create_packlist(value[i])
            packlist += new_list
        return packlist


class BinaryStructure(StructObject):
    """
    This is the core binary struct class that will need used.
    """

    def __init__(self, structure_dict):
        """
        Initialize this class with a structure ordereddict (see example in the tests) to get an object
        you can use to convert back and forth from binary data and dicts
        :param structure_dict: ordereddict of the ALLCAPS types.  Can be nested to create complex structs
        """
        self.structure_dict = structure_dict

        self.format = ''

        for k, v in self.structure_dict.items():
            if isinstance(v, OrderedDict):
                new_binarystructure = BinaryStructure(v)
                self.structure_dict[k] = new_binarystructure
                v = new_binarystructure

            self.format += v.format

        self.struct = struct.Struct(self.format)

    def __reduce__(self):
        return (self.__class__, (self.structure_dict,))

    def create_packlist(self, value):
        """
         returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
        :return:
        """
        data_list = []
        keys = list(self.structure_dict.keys())

        for k in keys:
            struct_type = self.structure_dict[k]
            val = value.get(k)  # will return None if the key is missing
            data_list += struct_type.create_packlist(val)

        return data_list

    def parse_unpacked(self, unpacked_data):
        # final_dict = OrderedDict()
        final_dict = {}

        keys = list(self.structure_dict.keys())

        unpack_offset = 0
        for x in range(len(keys)):
            key = keys[x]
            format_type = self.structure_dict[key]
            final_dict[key], new_offset = format_type.parse_unpacked(unpacked_data[x + unpack_offset:])
            unpack_offset += new_offset - 1

        return final_dict, len(keys) + unpack_offset


def run_tests():
    test4()
    test3()
    test2()
    test1()


def test4():
    original_input = b'\xAB'
    result = UINT8.unpack(original_input)
    assert (result == 0xAB)
    print('Passed Simple Data Unpack')

    result2 = UINT8.pack(171)
    assert (result2 == original_input)
    print('Passed Simple Data Pack')


def test3():
    original_input = b'\xFFThisIsAStringOfLength25\x00\x00\xEE'
    test_dict = OrderedDict()
    test_dict['starting_FF'] = UINT8
    test_dict['str'] = STRING(25)
    test_dict['ending_EE'] = UINT8
    test_structure = BinaryStructure(test_dict)

    result = test_structure.unpack(original_input)

    expected_dict = {'starting_FF': 0xFF,
                     'str': 'ThisIsAStringOfLength25',
                     'ending_EE': 0xEE}

    assert (result == expected_dict)
    print('Passed Null Terminated String Unpacking')

    result2 = test_structure.pack(expected_dict)

    assert (result2 == original_input)
    print('Passed Null Terminated String Packing')


def test2():
    original_input = b'\xFF' + b'\x01\x02\x03\x04\x00\x05\x06\x07\x08\x09' * 2 + b'\xEE'
    test_dict = OrderedDict()
    test_dict['one'] = UINT8
    test_dict['two'] = UINT8
    test_dict['nested'] = OrderedDict()
    test_dict['nested']['three'] = UINT8
    test_dict['nested']['four'] = UINT8
    test_dict['nested']['pad1'] = SPARE(1)
    test_dict['nested']['five'] = UINT8
    test_dict['six'] = UINT8
    test_dict['array'] = ARRAY(UINT8, 3)
    test_structure = BinaryStructure(test_dict)

    test_dict2 = OrderedDict()
    test_dict2['starting_FF'] = UINT8
    test_dict2['two_substructs'] = ARRAY(test_structure, 2)
    test_dict2['ending_EE'] = UINT8

    test_structure2 = BinaryStructure(test_dict2)
    result = test_structure2.unpack(original_input)

    expected_subdict = {'one': 1,
                        'two': 2,
                        'nested': {'three': 3,
                                   'four': 4,
                                   'pad1': None,
                                   'five': 5},
                        'six': 6,
                        'array': [7, 8, 9]}
    expected_dict = {'starting_FF': 0xFF,
                     'two_substructs': [expected_subdict, expected_subdict],
                     'ending_EE': 0xEE}
    assert (expected_dict == result)
    print('Complex Nest Unpack Pass')

    # Now lets go the other way
    result2 = test_structure2.pack(expected_dict)
    assert (result2 == original_input)
    print('Complex Nest Pack Pass')

    expected_subdict2 = {'one': 1,
                         'two': 2,
                         'nested': {'three': 3,
                                    'four': 4,
                                    'five': 5},
                         'six': 6,
                         'array': [7, 8, 9]}
    expected_dict2 = {'starting_FF': 0xFF,
                      'two_substructs': [expected_subdict2, expected_subdict2],
                      'ending_EE': 0xEE}

    result3 = test_structure2.pack(expected_dict2)
    assert (result3 == original_input)
    print('Complex Nest Pack Pass Without Padding')


def test1():
    original_input = b'\x01\x02\x03\x04\x00\x05\x06\x07\x08\x09'
    test_dict = OrderedDict()
    test_dict['one'] = UINT8
    test_dict['two'] = UINT8
    test_dict['nested'] = OrderedDict()
    test_dict['nested']['three'] = UINT8
    test_dict['nested']['four'] = UINT8
    test_dict['nested']['pad1'] = SPARE(1)
    test_dict['nested']['five'] = UINT8
    test_dict['six'] = UINT8
    test_dict['array'] = ARRAY(UINT8, 3)
    test_structure = BinaryStructure(test_dict)

    # unpack the data and we'll compare it against what we should have gotten
    result = test_structure.unpack(original_input)
    # for completeness, we compare expect the dict that returns to have a pad1 value of None.
    expected_dict = {'one': 1,
                     'two': 2,
                     'nested': {'three': 3,
                                'four': 4,
                                'pad1': None,
                                'five': 5},
                     'six': 6,
                     'array': [7, 8, 9]}

    assert (expected_dict == result)
    print('test unpack OK')

    # Now we re-build the original data bytes from what we expected and should get what we started with.
    result2 = test_structure.pack(expected_dict)
    assert (original_input == result2)
    print('test pack OK')

    # because the padding is optional, we shouldn't need to supply it when packing the data
    expected_dict_nopad = {'one': 1,
                           'two': 2,
                           'nested': {'three': 3,
                                      'four': 4,
                                      'five': 5},
                           'six': 6,
                           'array': (7, 8, 9)}

    result3 = test_structure.pack(expected_dict_nopad)
    assert (original_input == result3)
    print('test pack without pad OK')


if __name__ == '__main__':
    run_tests()