#!/usr/bin/env python
# salsa 0.0.1
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

import os
import glob
import dx_utils
import dxpy

@dxpy.entry_point('main')
def main(input_assembly, hic_alignments, restriction_enzyme_bases, filter_alignments, input_assembly_graph=None):
    # make sure we can run salsa
    dx_utils.run_cmd("python /opt/SALSA/run_pipeline.py -h")

    input_assembly = dx_utils.download_and_gunzip_file(input_assembly)
    alignment_prefix=input_assembly.split(".fasta")[0]

    # process inputs and convert to bed
    first_file = True
    for bam_file in hic_alignments:
        fn = dxpy.describe(bam_file['$dnanexus_link'])['name']
        cmd = 'dx cat {0}'.format(bam_file['$dnanexus_link'])
        prefix, suffix = os.path.splitext(fn)
        if suffix == '.gz':
            cmd += '| gunzip '
            fn = prefix
        cmd += '| bedtools bamtobed -i stdin'
        if first_file:
           cmd += ' > {0}.bed'.format(alignment_prefix)
           first_file = False
        else:
           cmd += ' >> {0}.bed'.format(alignment_prefix)
        dx_utils.run_cmd(cmd)

    # index the ref
    cmd = 'samtools faidx {0} '.format(input_assembly)
    dx_utils.run_cmd(cmd)

    # if we were asked to filter by contig names, make a bed file and subset the input bed
    if filter_alignments == True:
        f = open('%s.fai' %(input_assembly))
        o = open("%s.contigs.bed"%(alignment_prefix), 'w')
        for line in f:
           line = line.strip().split()
           o.write("%s\t1\t%s\n"%(line[0], line[1]))

        f.close()
        o.close()
 
        cmd = 'bedtools intersect -wa -a {0}.bed -b {0}.contigs.bed > {0}.filtered.bed'.format(alignment_prefix)
        dx_utils.run_cmd(cmd)
    else:
        cmd = 'ln -s {0}.bed {0}.filtered.bed'.format(alignment_prefix)
        dx_utils.run_cmd(cmd)

    # now sort the bed file
    cmd = "sort -T . -k4 {0}.filtered.bed > {0}.sorted.bed".format(alignment_prefix)
    dx_utils.run_cmd(cmd)

    cmd = 'python /opt/SALSA/run_pipeline.py -a {0} -b {1}.sorted.bed -l {0}.fai -o {2} -e {3} -m yes -p yes '
    cmd = cmd.format(input_assembly, alignment_prefix, './', ','.join(restriction_enzyme_bases))
    if input_assembly_graph is not  None:
        cmd = "%s -g input_assembly_graph"%(cmd)

    dx_utils.run_cmd(cmd)

    output = {}
    
    # final scaffold
    final_fasta = 'scaffold*FINAL.fasta'
    output['scaffold_fasta'] = dx_utils.gzip_and_upload(final_fasta)

    # final agp
    final_agp = 'scaffold*FINAL.agp'
    output['scaffold_agp'] = dx_utils.gzip_and_upload(final_agp)

    # all others
    files = glob.glob('scaffold*fasta')
    files.extend( glob.glob('scaffold*agp'))
    files.pop(final_fasta)
    files.pop(final_agp)
    print files
    
    output['scaffold'] = dx_utils.tar_files_and_upload(files, alignment_prefix)

    return output

dxpy.run()
