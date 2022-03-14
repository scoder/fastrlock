
def suite():
    import unittest
    import doctest
    import os
    test_dir = os.path.abspath(os.path.dirname(__file__))

    tests = []
    for filename in os.listdir(test_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            tests.append(unittest.defaultTestLoader.loadTestsFromName(__name__ + '.' + filename[:-3]))

    suite = unittest.TestSuite(tests) if len(tests) != 1 else tests[0]
    suite.addTest(doctest.DocFileSuite('../../README.rst'))
    return suite


if __name__ == '__main__':
    import unittest
    unittest.main()
