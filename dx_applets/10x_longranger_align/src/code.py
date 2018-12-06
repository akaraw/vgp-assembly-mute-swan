#!/usr/bin/env python
# bax_to_bam 0.0.1
# Generated by dx-app-wizard.
#
# Basic execution pattern: Your app will run on a single machine from
# beginning to end.
#
# See https://wiki.dnanexus.com/Developer-Portal for documentation and
# tutorials on how to modify this file.
#
# DNAnexus Python Bindings (dxpy) documentation:
#   http://autodoc.dnanexus.com/bindings/python/current/

import glob
import os
import subprocess

import dxpy


os.environ['PATH'] = '/longranger-2.2.2' + os.pathsep + os.environ['PATH']


def run_cmd(cmd, returnOutput=False):
    print cmd
    if returnOutput:
        output = subprocess.check_output(cmd, shell=True, executable='/bin/bash').strip()
        print output
        return output
    else:
        subprocess.check_call(cmd, shell=True, executable='/bin/bash')


def remove_special_chars(string):
    '''function that replaces any characters in a string that are not alphanumeric or _ or .'''
    string = "".join(
        char for char in string if char.isalnum() or char in ['_', '.'])

    return string


def untar_to_work_dir(targz_link, target_dir, added_args=''):
    input_file = dxpy.DXFile(targz_link)
    input_filename = input_file.describe()['name']

    cmd = 'dx download ' + input_file.get_id() + ' -o - '
    if input_filename.endswith('.tar.gz'):
        cmd += '| tar -xzvf - -C {0} '.format(target_dir)
    elif input_filename.endswith('.tar'):
        cmd += '| tar -xvf - -C {0} '.format(target_dir)
    cmd += added_args

    run_cmd(cmd)


def download_and_gunzip_file(input_file, skip_decompress=False, additional_pipe=None):
    input_file = dxpy.DXFile(input_file)
    input_filename = input_file.describe()['name']
    ofn = remove_special_chars(input_filename)

    cmd = 'dx download ' + input_file.get_id() + ' -o - '
    if input_filename.endswith('.tar.gz'):
        ofn = 'tar_output_{0}'.format(ofn.replace('.tar.gz', ''))
        cmd += '| tar -zxvf - '
    elif (os.path.splitext(input_filename)[-1] == '.gz') and not skip_decompress:
        cmd += '| gunzip '
        ofn = os.path.splitext(ofn)[0]
    if additional_pipe is not None:
        cmd += '| ' + additional_pipe
    cmd += ' > ' + ofn
    print cmd
    subprocess.check_call(cmd, shell=True)

    return ofn


@dxpy.entry_point('main')
def main(**job_inputs):
    fastq_files = job_inputs['fastq_tars']

    fastq_dir = '/home/dnanexus/fastqs'
    run_cmd('mkdir {0} --parents'.format(fastq_dir))

    # check to see what kind of file the fastqs are
    one_fastq_file = dxpy.DXFile(fastq_files[0])
    one_fastq_file = one_fastq_file.describe()['name']

    if one_fastq_file.endswith('.tar.gz') or one_fastq_file.endswith('.tar'):
        for tar_file in fastq_files:
            untar_to_work_dir(tar_file, fastq_dir)
    else:
        for f in fastq_files:
            fastq_file = download_and_gunzip_file(f)
            if fastq_file.endswith('.fq'):
                new_file = os.path.join(fastq_dir, fastq_file.replace('.fq', '.fastq'))
            else:
                new_file = os.path.join(fastq_dir, fastq_file)
            run_cmd('mv {0} {1}'.format(fastq_file, new_file))

    ref_dir = '/home/dnanexus/ref'
    run_cmd('mkdir {0} --parents'.format(ref_dir))

    untar_to_work_dir(job_inputs['ref'], ref_dir, added_args='--strip-components 1')

    run_cmd('longranger align --help')

    longranger_cmd = 'longranger align --disable-ui --id {id} --fastqs {fastq_dir} --reference {ref_dir} '.format(
        id=job_inputs['output_prefix'], fastq_dir=fastq_dir, ref_dir=ref_dir)

    if 'sample_name' in job_inputs:
        longranger_cmd += '--sample {0} '.format(job_inputs['sample_name'])

    if 'lanes' in job_inputs:
        longranger_cmd += '--lanes {0} '.format(job_inputs['lanes'])

    if 'indices' in job_inputs:
        longranger_cmd += '--indices {0} '.format(job_inputs['indices'])

    run_cmd(longranger_cmd)

    output_dir = '/home/dnanexus/{0}/outs'.format(job_inputs['output_prefix'])

    run_cmd('tree {0}'.format(output_dir))

    sorted_bam = os.path.join(output_dir, 'possorted_bam.bam')
    sorted_bam_index = os.path.join(output_dir, 'possorted_bam.bam.bai')
    summary_file = os.path.join(output_dir, 'summary.csv')

    output = {'sorted_bam': dxpy.dxlink(dxpy.upload_local_file(sorted_bam)),
              'sorted_bam_index': dxpy.dxlink(dxpy.upload_local_file(sorted_bam_index)),
              'summary': dxpy.dxlink(dxpy.upload_local_file(summary_file))}
    return output

dxpy.run()