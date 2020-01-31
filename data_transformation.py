from __future__ import absolute_import
import argparse
import csv
import logging
import os

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io.gcp.bigquery import parse_table_schema_from_json


class DataTransformation:
    def __init__(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.schema_str = ''
        schema_file = os.path.join(dir_path, 'resources', 'usa_names.json')
        with open(schema_file) as f:
            data = f.read()
            self.schema_str = '{"fields": ' + data + '}'


    def parse_method(self, string_input):
        schema = parse_table_schema_from_json(self.schema_str)
        field_map = [f for f in schema.fields]
        reader = csv.reader(string_input.split('\n'))
        for csv_row in reader:
            values = [x for x in csv_row]
            values[-1] = int(values[-1]) * 2
            values[-2] = values[-2][::-1]
            row = {}
            i = 0
            for value in values:
                row[field_map[i].name] = value
                i += 1
            return row


def run(argv=None):
    """The main function which creates the pipeline and runs it."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input', dest='input', required=False,
        help='Input file to read.  This can be a local file or '
             'a file in a Google Storage Bucket.',
        default='gs://jenit-bukcet/usa_names.csv')
    parser.add_argument('--output', dest='output', required=False,
                        help='Output BQ table to write results to.',
                        default='jenit_data.usa_names_transformed2')

    known_args, pipeline_args = parser.parse_known_args(argv)
    data_ingestion = DataTransformation()

    p = beam.Pipeline(options=PipelineOptions(pipeline_args))
    schema = parse_table_schema_from_json(data_ingestion.schema_str)

    (p
     | 'Read From Text' >> beam.io.ReadFromText(known_args.input,
                                                skip_header_lines=1)
     | 'String to BigQuery Row' >> beam.Map(lambda s:
                                            data_ingestion.parse_method(s))
     | 'Write to BigQuery' >> beam.io.Write(
        beam.io.BigQuerySink(
            known_args.output,
            schema=schema,
            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=beam.io.BigQueryDisposition.WRITE_TRUNCATE)))
    p.run().wait_until_finish()


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()

