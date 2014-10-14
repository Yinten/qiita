from os.path import join
from tempfile import mkdtemp
from gzip import open as gzopen

from .processing_pipeline import StudyPreprocessor
from qiita_core.qiita_settings import qiita_config
from qiita_ware.commands import submit_EBI_from_files
from qiita_ware.demux import to_per_sample_ascii
from qiita_ware.util import open_file
from qiita_db.study import Study
from qiita_db.metadata_template import SampleTemplate, PrepTemplate
from qiita_db.data import PreprocessedData, RawData
from qiita_db.parameters import PreprocessedIlluminaParams


def split_libraries(study_id, raw_data_id, param_id):
    study = Study(study_id)
    raw_data = RawData(raw_data_id)
    params = PreprocessedIlluminaParams(param_id)

    sp = StudyPreprocessor()
    return sp(study, raw_data, params)


def submit_to_ebi(study_id):
    """Submit a study to EBI"""
    study = Study(study_id)
    st = SampleTemplate(study.sample_template)
    raw_data_id = study.preprocessed_data()[0]
    pt = PrepTemplate(raw_data_id)
    preprocessed_data = PreprocessedData(raw_data_id)
    investigation_type = RawData(raw_data_id).investigation_type

    demux = [path for path, ftype in preprocessed_data.get_filepaths()
             if ftype == 'preprocessed_demux'][0]

    tmp_dir = mkdtemp(prefix=qiita_config.working_dir)
    output_dir = tmp_dir + '_submission'

    samp_fp = join(tmp_dir, 'sample_metadata.txt')
    prep_fp = join(tmp_dir, 'prep_metadata.txt')

    st.to_file(samp_fp)
    pt.to_file(prep_fp)

    with open_file(demux) as demux_fh:
        for samp, iterator in to_per_sample_ascii(demux_fh, list(st)):
            with gzopen(join(tmp_dir, "%s.fastq.gz" % samp), 'w') as fh:
                for record in iterator:
                    fh.write(record)

    return submit_EBI_from_files(study_id, open(samp_fp), open(prep_fp),
                                 tmp_dir, output_dir, investigation_type,
                                 'ADD', True)
