import os
import shlex
import subprocess
import logging
import argparse
import pathlib
from Bio import SeqIO
from Bio import Entrez
from Bio import SearchIO
from Bio.Seq import Seq
from Bio.Blast import NCBIWWW
curr =  os.getcwd()
os.chdir(curr)


def arg_parser():
    parser = argparse.ArgumentParser(description='some description')
    parser.add_argument('srrfiles', metavar= '.srr', type=str, nargs = '*', help = 'SRRs')

    return parser.parse_args()




def InptFiles(SRR):
    """
    This will retrieve the transcriptomes of given SRR numbers and convert them to
    paired-end fastq files. Files from wget download as SRR#######.1 get renamed to SRR#######  

    """
    #getFiles = 'wget https://sra-download.st-va.ncbi.nlm.nih.gov/sos1/sra-pub-run-12/SRR' + SRR + '/' + SRR + '.1'
    #wget https://sra-download.st-va.ncbi.nlm.nih.gov/sos1/sra-pub-run/12/SRR5660030/SRR5660030.1
    renameFile = 'mv '+ str(SRR)+'.1 ' + SRR
    splitFiles = 'fastq-dump -I --split-files '+ str(SRR)
    #os.system(getFiles)
    os.system(renameFile)
    os.system(splitFiles)

#    rename_file_cmd = shlex.split('mv {}.1 {}'.format(SRR, SRR))
#    with open('mv_cmd_log.txt', 'ab+') as mv_out:
#        subprocess.run(rename_file_cmd, stdout=mv_out, stderr=mv_out)

#    split_files_cmd = shlex.split('fastq-dump -I --split-files {}'.format(SRR))
#    with open('fastq_dump_output.txt', 'ab+') as fastq_dump_out:
#        subprocess.run(split_files_cmd, stdout=fastq_dump_out, stderr=fastq_dump_out)

def getTranscriptomeIndex():
    outFasta = open("EF999921.fasta", "w")
    outFile = open("EF999921_CDS.fasta","w")
    Entrez.email = 'kdelany@luc.edu'
    handle = Entrez.efetch(db = 'nucleotide', id= 'EF999921', rettype= 'fasta')
    records = list(SeqIO.parse(handle, "fasta"))
    outFasta.write('>' + str(records[0].description)+ '\n' + str(records[0].seq))
    outFasta.close()
    #SeqIO.write(records[0], 'EF999921.fasta', 'fasta')
    GBhandle = Entrez.efetch(db = 'nucleotide', id = 'EF999921', rettype= 'gb', retmode='text')
    count = 0
    for record in SeqIO.parse(GBhandle, 'genbank'):
            for feature in record.features:
                if feature.type == "CDS":
                    count +=1
                    outFile.write('>' + str(feature.qualifiers['protein_id']).replace('[', '').replace(']', '').replace("'","") + '\n' + str(feature.location.extract(record).seq) +'\n')                
    outFile.close()
    return(count)



def Kallisto(SRR):
    """
    Takes in SRR number and creates/runs the Kallisto command line commands.
    Uses CDS fasta file created in the transcriptome index

    """
    kallisto_cmd = 'time kallisto index -i HCMVindex.idx EF999921_CDS.fasta'
    os.system(kallisto_cmd)
    kallisto_run = 'time kallisto quant -i HCMVindex.idx -o ./' + str(SRR) +' -b 30 -t 4 '+ str(SRR) + '_1.fastq '+ str(SRR)+ '_2.fastq'
    os.system(kallisto_run)



def SleuthInput():
    SRRs = 'SRR5660030','SRR5660033','SRR5660044','SRR5660045'
    covFile = open('cov.txt','w')
    condition1 = "2dpi"
    condition2 = "6dpi"
    covFile.write('sample'+ '\t' + 'condition' + '\t' + 'path' + '\n')
    for i in SRRs:
        path = '/data/kdelany/compBio_miniProject/'+i
        if int(i[3:])%2==0:
            covFile.write(str(i)+ '\t' + condition1 + '\t'+ str(path)+ '\n')
        else:
            covFile.write(str(i)+ '\t' + condition2 + '\t'+ str(path)+ '\n')
    covFile.close()


def Sleuth():
    runSleuth = 'Rscript sleuth.R'
    os.system(runSleuth)
    output = open('topten.txt','r')
    listoflines= output.readlines()
    for line in listoflines:
        logging.info(line)



def bowtie2build(SRR):
    """ Builds a Bowtie index for HCMV """
    build_cmd = 'bowtie2-build ./EF999921.fasta HCMV'
    os.system(build_cmd)
    bowtie_cmd = 'bowtie2 --quiet --al-conc --no-unal -x HCMV -1 '+SRR+'_1.fastq -2'+SRR+'_2.fastq -S '+SRR+ '.sam'
    os.system(bowtie_cmd)



def Sam2Fastq(SRR):
    """ Bash script to convert sam files to fastq files """
    runConvert = 'bash samtofastq.sh ' + str(SRR)
    os.system(runConvert)



def getNumReads(SRR):
    """ Returns the number of reads before bowtie2 and after """
    name = ''
    #tells which donor to write into log file
    if SRR == 'SRR5660030':
        name = 'Donor 1 (2dpi)'
    elif SRR == 'SRR5660033':
        name = 'Donor 1 (6dpi)'
    elif SRR == 'SRR5660044':
        name = 'Donor 3 (2dpi)'
    else:
        name = 'Donor 3 (6dpi)'
    SRRfile = open(str(SRR)+'_1.fastq')
    SRRfile1 = open(str(SRR)+'_2.fastq')
    count1 = 0
    count = 0
    #count reads in SRR file before bowtie
    for line in SRRfile:
        count1+=1
    for line in SRRfile1:
        count+=1               
    beforeCount =(count+ count1)/4
    AfterFile = open(str(SRR)+'_bow.fastq')
    #count reads after bowtie mapping
    count2 = 0
    for line in AfterFile:
        count2 +=1
    afterCount = count2/4

    logging.info(str(name)+' had ' +str(beforeCount) + ' read pairs before Bowtie2 filtering and '+ str(afterCount)+' pairs after.')



def SPAdes(SRRs):
    SRR1= SRRs[0]
    SRR2= SRRs[1]
    SRR3= SRRs[2]
    SRR4= SRRs[3]
    spades_cmd = 'spades -k 55,77,99,127 -t 2 --only-assembler -s '+SRR1+'_bow.fastq -s '+SRR2+'_bow.fastq -s '+SRR3+ '_bow.fastq -s '+SRR4 + '_bow.fastq -o SpadesAssembly/'
    os.system(spades_cmd)
   
    logging.info(str(spades_cmd))



def numContigs():
    newFile = open('LargeContigs.txt', 'w')
    count = 0
    handle = SeqIO.parse('./SpadesAssembly/contigs.fasta','fasta')
    for record in handle:
        m = len(record.seq)
        if m > 1000:
            count +=1
            newFile.write('> '+str(record.id) + '\n' + str(record.seq) + '\n')
    newFile.close()

    logging.info('There are '+str(count)+' contigs > 1000 bp in the assembly.')



def countContigs():
    newFile = open('LargeContigs.txt', 'r')
    handle = SeqIO.parse('LargeContigs.txt', 'fasta')
    lenList = []
    for record in handle:
        m = len(record.seq)
        lenList.append(int(m))    
    total = sum(lenList) 
   
    logging.info('There are '+str(total)+' bp in the assembly.')


def assembleContigs():
    assemblyFile = open('Assemble.fasta','w')
    inFile = open('LargeContigs.txt','r')
    handle = SeqIO.parse(inFile, 'fasta')
    concat = ''
    for record in handle:
        seq = str(record.seq)
        concat+= seq+ 'NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN'
    assemblyFile.write(concat)
    assemblyFile.close()


def blast():
    inFile = open('Assemble.fasta').read()
    blast1 = NCBIWWW.qblast('blastn','nr',inFile, entrez_query='10292[taxid]')
    with open('my_blast.xml', 'w') as outhandle:
        outhandle.write(blast1.read())
    outhandle.close()
    blast_record = SearchIO.read('my_blast.xml','blast-xml')
    addResult = ''
    logging.info('seq_title\talign_len\tnumber_HSPs\ttopHSP_ident\ttopHSP_gaps\ttopHSP_bits\ttopHSP_expect')
    for alignment in blast_record.alignments:
        for hsp in alignment.hsps:
            seq_title = str(hsp.id)
            align_len = str(hsp.seq_len)
            number_HSPs = str(len(hsp.hsps))
            topHSP_ident = str(hsp.ident_num)
            topHSP_gaps = str(gap_num)
            topHSP_bits = str(hsp.bitscore)
            topHSP_expect = str(hsp.evalue)
            logging.info(seq_title + '\t' + align_len+ '\t'+ number_HSPs+ '\t'+topHSP_ident+ '\t'+ topHSP_gaps+ '\t'+ topHSP_bits+ '\t'+ topHSP_expect)



def main():
    """ Takes in SRR id number arguments in command line and runs through"""
    
    # parser = argparse.ArgumentParser(description= 'Process SRR (RunID) numbers')
    # parser.add_argument('SRR', metavar= 'N', type=str, nargs = '+', help = 'SRRs')
    args = arg_parser()
    
    logging.info('SRA values: %s', args.srrfiles)

    print(args.srrfiles)
    
#    for i in args.SRR:
#       InptFiles(i)
#    with open('miniproject.log', 'a') as f_out:
#        f_out.write('SRA files download done.')
#        f_out.close()
#    result =  getTranscriptomeIndex()
#    logging.info('The HCMV genome (EF999921) has '+str(result))


    

#    for i in args.SRR:
#        Kallisto(i)

#    SleuthInput()
##still have to run R code in command line
    
    SRRs = []
#    for i in args.SRR:
       # bowtie2build(i)
#        Sam2Fastq(i)
#        getNumReads(i)
#        SRRs.append(i)
#    SPAdes(SRRs)

#    numContigs()
    countContigs()
    assembleContigs()
    blast()  





    
if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logFormatter = '%(message)s'
    logging.basicConfig(filename='some_log.log', format=logFormatter, level=logging.DEBUG)
    main()
