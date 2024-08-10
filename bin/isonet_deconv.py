import logging
import os, sys, traceback
from TomoNet.util.dict2attr import Arg, check_parse, idx2list
from TomoNet.util.metadata import MetaData, Label, Item

def deconv(self, star_file: str,
    deconv_folder:str="./deconv",
    voltage: float=300.0,
    cs: float=2.7,
    snrfalloff: float=None,
    deconvstrength: float=None,
    highpassnyquist: float=0.02,
    chunk_size: int=None,
    overlap_rate: float= 0.25,
    ncpu:int=4,
    tomo_idx: str=None):
    """
    \nCTF deconvolution for the tomograms.\n
    isonet.py deconv star_file [--deconv_folder] [--snrfalloff] [--deconvstrength] [--highpassnyquist] [--overlap_rate] [--ncpu] [--tomo_idx]
    This step is recommended because it enhances low resolution information for a better contrast. No need to do deconvolution for phase plate data.
    :param deconv_folder: (./deconv) Folder created to save deconvoluted tomograms.
    :param star_file: (None) Star file for tomograms.
    :param voltage: (300.0) Acceleration voltage in kV.
    :param cs: (2.7) Spherical aberration in mm.
    :param snrfalloff: (1.0) SNR fall rate with the frequency. High values means losing more high frequency.
    If this value is not set, the program will look for the parameter in the star file.
    If this value is not set and not found in star file, the default value 1.0 will be used.
    :param deconvstrength: (1.0) Strength of the deconvolution.
    If this value is not set, the program will look for the parameter in the star file.
    If this value is not set and not found in star file, the default value 1.0 will be used.
    :param highpassnyquist: (0.02) Highpass filter for at very low frequency. We suggest to keep this default value.
    :param chunk_size: (None) When your computer has enough memory, please keep the chunk_size as the default value: None . Otherwise, you can let the program crop the tomogram into multiple chunks for multiprocessing and assembly them into one. The chunk_size defines the size of individual chunk. This option may induce artifacts along edges of chunks. When that happen, you may use larger overlap_rate.
    :param overlap_rate: (None) The overlapping rate for adjecent chunks.
    :param ncpu: (4) Number of cpus to use.
    :param tomo_idx: (None) If this value is set, process only the tomograms listed in this index. e.g. 1,2,4 or 5-10,15,16
    """
    from IsoNet.util.deconvolution import deconv_one

    logging.basicConfig(format='%(asctime)s, %(levelname)-8s %(message)s',
    datefmt="%m-%d %H:%M:%S",level=logging.INFO,handlers=[logging.StreamHandler(sys.stdout)])
    logging.info('\n######Isonet starts ctf deconvolve######\n')

    try:
        md = MetaData()
        md.read(star_file)
        if not 'rlnSnrFalloff' in md.getLabels():
            md.addLabels('rlnSnrFalloff','rlnDeconvStrength','rlnDeconvTomoName')
            for it in md:
                md._setItemValue(it,Label('rlnSnrFalloff'),1.0)
                md._setItemValue(it,Label('rlnDeconvStrength'),1.0)
                md._setItemValue(it,Label('rlnDeconvTomoName'),None)

        if not os.path.isdir(deconv_folder):
            os.mkdir(deconv_folder)

        tomo_idx = idx2list(tomo_idx)
        for it in md:
            if tomo_idx is None or str(it.rlnIndex) in tomo_idx:
                if snrfalloff is not None:
                    md._setItemValue(it,Label('rlnSnrFalloff'), snrfalloff)
                if deconvstrength is not None:
                    md._setItemValue(it,Label('rlnDeconvStrength'),deconvstrength)

                tomo_file = it.rlnMicrographName
                base_name = os.path.basename(tomo_file)
                deconv_tomo_name = '{}/{}'.format(deconv_folder,base_name)

                deconv_one(it.rlnMicrographName,deconv_tomo_name,voltage=voltage,cs=cs,defocus=it.rlnDefocus/10000.0, pixel_size=it.rlnPixelSize,snrfalloff=it.rlnSnrFalloff, deconvstrength=it.rlnDeconvStrength,highpassnyquist=highpassnyquist,chunk_size=chunk_size,overlap_rate=overlap_rate,ncpu=ncpu)
                md._setItemValue(it,Label('rlnDeconvTomoName'),deconv_tomo_name)
            md.write(star_file)
        logging.info('\n######Isonet done ctf deconvolve######\n')

    except Exception:
        error_text = traceback.format_exc()
        f =open('log.txt','a+')
        f.write(error_text)
        f.close()
        logging.error(error_text)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_parse(sys.argv[1:])
