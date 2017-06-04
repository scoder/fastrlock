
def suite():
    import unittest
    import doctest
    import os
    test_dir = os.path.abspath(os.path.dirname(__file__))

    tests = []
    for filename in os.listdir(test_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            tests.append(unittest.findTestCases('tests.'+ filename[:-3]))

    suite = unittest.TestSuite(tests)
    suite.addTest(doctest.DocFileSuite('../../README.rst'))
    return suite


if __name__ == '__main__':
    import unittest
    unittest.main()
