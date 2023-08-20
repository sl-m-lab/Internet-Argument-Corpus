"""ConVote is a corpus of US congressional debate transcripts.

Inclusion of this dataset is intended to show importing a third party dataset.
Steps:
    Download the data from http://www.cs.cornell.edu/home/llee/data/convote.html
    Initialize the database using iacorpus/initialization/convote/convote.sql
    Populate the database using iacorpus/initialization/convote/convote_importer.py
"""

from iacorpus.datasets.generic.dataset import Dataset


class ConVoteDataset(Dataset):
    pass


def load_dataset(name='convote', **kwargs) -> ConVoteDataset:
    kwargs['name'] = name
    return ConVoteDataset(**kwargs)
