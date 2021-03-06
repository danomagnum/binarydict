# binarydict

A high level struct module for python that makes the default struct module human readable.  
The main use case I've found for this is pulling data out of binary files and raw tcp streams that are sending structs from the native language.

The basic idea is to create an OrderedDict for each struct.  You can nest them as desired.  This allows a fairly readable way to define structures and boils them downs to dictionaries so they are asy to use.

This also works in both directions.  A defined struct can unpack data from bytes into a dict and pack data from a dict into binary.  The dicts you create the structure with need to be OrderedDicts so the elements are maintained in the correct order, but you can use regular dicts for supplying the data to pack after that since it already has the order.

Example
```
from binary_dict import CHAR, SINT8, UINT8, BOOL, SINT16, UINT16, SINT32, UINT32,\
                        SINT64, UINT64, SINT_NATIVE, UINT_NATIVE, HALF, FLOAT, DOUBLE, \
                        STRING, SPARE, ARRAY, BinaryStructure
from collections import OrderedDict

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

# this is a binary stream that goes from 1-9
binary_input = b'\x01\x02\x03\x04\x00\x05\x06\x07\x08\x09'

result = test_structure.unpack(binary_input)

#result is a dict as shown below
#result = {'one': 1,
#          'two': 2,
#          'nested': {'three':3,
#                     'four': 4,
#                     'pad1': None,
#                     'five': 5},
#          'six': 6,
#          'array':[7,8,9]}

```

You can also nest structures themselves.

```
#continuing using test_structure from the last example.
# this structure consists of the byte 0xFF, two of the test_structures, and then the byte 0xEE.
test_dict2 = OrderedDict()
test_dict2['starting_FF'] = UINT8
test_dict2['two_substructs'] = ARRAY(test_structure, 2)
test_dict2['ending_EE'] = UINT8

test_structure2 = BinaryStructure(test_dict2)

#for the example we'll use two of the exact same substructs.  
#They could be different though of course.

binary_input = b'\xFF' + b'\x01\x02\x03\x04\x00\x05\x06\x07\x08\x09' * 2 + b'\xEE'


expected_subdict = {'one': 1,
                    'two': 2,
                     'nested': {'three':3,
                                'four': 4,
                                'pad1': None,
                                'five': 5},
                     'six': 6,
                     'array':[7,8,9]}

expected_dict = {'starting_FF': 0xFF,
                 'two_substructs':  [expected_subdict, expected_subdict],
                 'ending_EE': 0xEE}
 
result = test_structure2.unpack(original_input)

#result should now match expected_dict



```

If you need to convert a simple value, it's easy to use also.

```
value = UINT16.unpack(b'\x01\x46') # value = 17,921
value = FLOAT.pack(3.141592) # value = 0xD80F4940
value = ARRAY(FLOAT, 4).pack([1.2, 3.4, 5.6, 7.8]) # value = 9a 99 99 3f 9a 99 59 40 33 33 b3 40 9A 99 F9 40

```
