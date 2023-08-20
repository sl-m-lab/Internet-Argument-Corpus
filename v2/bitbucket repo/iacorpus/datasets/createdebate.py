from iacorpus.datasets.generic.dataset import Dataset


class CreateDebateDataset(Dataset):
    pass


def load_dataset(name='createdebate', **kwargs) -> CreateDebateDataset:
    kwargs['name'] = name
    return CreateDebateDataset(**kwargs)
