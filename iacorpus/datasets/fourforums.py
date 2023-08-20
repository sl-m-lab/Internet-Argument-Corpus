from iacorpus.datasets.generic.dataset import Dataset


class FourForumsDataset(Dataset):
    def get_qr_discussion_ids(self):
        return self.get_discussion_ids(tablename='mturk_2010_qr_entry')


def load_dataset(name='fourforums', **kwargs) -> FourForumsDataset:
    kwargs['name'] = name
    return FourForumsDataset(**kwargs)
