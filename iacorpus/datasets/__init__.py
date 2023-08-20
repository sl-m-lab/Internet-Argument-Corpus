"""iacorpus consists of a set of datasets.

In order to use iacorpus.load_dataset(name):
    a dataset should exist in a module iacorpus.datasets.<name>
    it should extend iacorpus.datasets.generic.Dataset
    it should provide its own load_dataset() function
    if it needs to alter the ORM beyond defaults it can include an orm module added to <dataset>._get_orms()
"""
