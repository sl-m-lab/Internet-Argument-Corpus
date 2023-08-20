from collections import defaultdict

import sqlalchemy

from iacorpus import load_connection
from iacorpus.utilities.misc import ProgressReporter, lazy_property


class RawDataLoader:
    """Loads data from disk, grouping as appropriate
    """
    def __init__(self, dataset_name, ordered_categories=None):
        self.dataset_name = dataset_name
        self.ordered_categories = ordered_categories

    @lazy_property
    def connection(self):
        return load_connection(self.dataset_name)

    def run(self, verbosity=2, skip_to=None):
        if verbosity > 0:
            print('grouping entries')
        grouped_entries = self.group_entries()  # {category: group_id: [details]}}
        if self.ordered_categories is None:
            self.ordered_categories = sorted(grouped_entries.keys())
        for category in self.ordered_categories:
            if verbosity > 0:
                print('Handling category:', category, 'Length:', len(grouped_entries[category]))
                progress = ProgressReporter(total_number=len(grouped_entries[category]))

            group_ids = list(grouped_entries[category].keys())
            self.maybe_sort_group_ids(group_ids)
            for group_id in group_ids:
                if skip_to is not None and group_id != skip_to:
                    progress.report()
                    continue
                skip_to = None
                if verbosity > 1:
                    print('Handling entry:', group_id)
                descriptors = grouped_entries[category][group_id]
                self.maybe_sort_descriptors(descriptors)
                entries_raw_data = [self.load_raw_data(descriptor) for descriptor in descriptors]
                yield category, group_id, entries_raw_data
                if verbosity > 0:
                    progress.report()

    def group_entries(self):
        descriptors = self.get_descriptors()
        grouped_entries = defaultdict(lambda: defaultdict(list))  # {category: group_id: [details]}}
        for descriptor in descriptors:
            category = self.get_category(descriptor)
            if category is not None:
                group_id = self.get_group_id(descriptor)
                grouped_entries[category][group_id].append(descriptor)
        return grouped_entries

    def get_category(self, descriptor):
        """Override me!
        to ignore:
         return None
        for discussions:
         return 'discussion'
        for user pages:
         return 'author'
        etc.
        """
        return 'discussion'

    def get_group_id(self, descriptor):
        """Override me!"""
        return descriptor['url']

    def maybe_sort_group_ids(self, group_ids):
        group_ids.sort()

    def get_descriptors(self):
        return self.get_db_raw_html_descriptors()

    def get_db_raw_html_descriptors(self):
        raw_html_table = sqlalchemy.Table('raw_html', self.connection['metadata'], autoload=True)
        stmt = sqlalchemy.select([raw_html_table.c.id, raw_html_table.c.actual_url.label('url')])
        query_result = stmt.execute()
        entries = [dict(entry) for entry in query_result]
        return entries

    def maybe_sort_descriptors(self, descriptors):
        descriptors.sort()

    def load_raw_data(self, descriptor):
        return self.load_db_raw_html_data(descriptor)

    def load_db_raw_html_data(self, descriptor):
        raw_html_table = sqlalchemy.Table('raw_html', self.connection['metadata'], autoload=True)
        stmt = sqlalchemy.select([raw_html_table.c.html], raw_html_table.c.id == descriptor['id'])
        query_result = stmt.execute()
        html = query_result.scalar()
        return html
