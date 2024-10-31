LIST_NAMES = ["Motion Correction", "3D Reconstruction", "CTF Estimation", "IsoNet", "Manual Picking", "Auto Expansion", "AI AutoPicking", "Other Utilities"]

header_labels_recon = ['Tomo Name', 'Action', 'Action', 'Action', 'Action', 'Action', 'Recon Map', 'Tilts #', \
    'RE mean', 'RE range', 'Binning', 'Thickness', 'Skipped view(s)', 'Notes']

header_labels_aretomo = ['Tomo Name', 'Action', 'Recon Map', 'Tilts #', \
    'Binning', 'Thickness', 'Skipped view(s)', 'Notes']

header_labels_prediction = ['Tomo Name', 'Particle #', 'Action']

header_labels_manual = ['Tomo Name', 'Top(one point)', 'Bottom(one point)', \
                        'Side(two points)', 'Action', 'Action', 'Action','Action']

header_labels_ctffind = ['Tomo Name', 'Tilt #', 'defocus (Å)', 'Best CTF ring fit at (Å)', 'Action', 'Action']

header_labels_expand = ['Tomo Name', 'Rounds # ', 'Final Particle #', 'Action', 'Action']

newst_com_params = ['AntialiasFilter', 'TransformFile', 'TaperAtFill', 'AdjustOrigin', 'SizeToOutputInXandY',\
                    'OffsetsInXandY', 'ImagesAreBinned', 'BinByFactor']

tilt_com_params = ['IMAGEBINNED', 'TILTFILE', 'THICKNESS', 'RADIAL', 'FalloffIsTrueSigma',\
                    'XAXISTILT', 'SCALE', 'PERPENDICULAR', 'MODE', 'FULLIMAGE', 'SUBSETSTART',\
                    'AdjustOrigin', 'LOCALFILE', 'ActionIfGPUFails', 'XTILTFILE', 'OFFSET', 'SHIFT',\
                    'FakeSIRTiterations', 'EXCLUDELIST', 'EXCLUDELIST2']

relion_particle_header = "\
data_particles\
loop_\
_rlnTomoName #1\
_rlnTomoParticleId #2\
_rlnTomoManifoldIndex #3\
_rlnCoordinateX #4\
_rlnCoordinateY #5\
_rlnCoordinateZ #6\
_rlnOriginXAngst #7\
_rlnOriginYAngst #8\
_rlnOriginZAngst #9\
_rlnAngleRot #10\
_rlnAngleTilt #11\
_rlnAnglePsi #12\
_rlnClassNumber #13\
_rlnRandomSubset #14\
"


import sys
from collections import OrderedDict
import copy



LABELS = {
    'rlnImageName': str,
    'rlnCubeSize':int,
    'rlnCropSize':int,
    'rlnSnrFalloff':float,
    'rlnDeconvStrength':float,
    'rlnPixelSize':float,
    'rlnDefocus':float,
    'rlnCorrectedTomoName':str,
    'rlnNumberSubtomo': int,
    'rlnMaskName': str,
    'rlnVoltage': float,
    'rlnDefocusU': float,
    'rlnDefocusV': float,
    'rlnDefocusAngle': float,
    'rlnSphericalAberration': float,
    'rlnDetectorPixelSize': float,
    'rlnCtfFigureOfMerit': float,
    'rlnMagnification': float,
    'rlnAmplitudeContrast': float,
    'rlnOriginalName': str,
    'rlnCtfImage': str,
    'rlnCoordinateX': float,
    'rlnCoordinateY': float,
    'rlnCoordinateZ': float,
    'rlnNormCorrection': float,
    'rlnMicrographName': str,
    'rlnGroupName': str,
    'rlnGroupNumber': str,
    'rlnOriginX': float,
    'rlnOriginY': float,
    'rlnAngleRot': float,
    'rlnAngleTilt': float,
    'rlnAnglePsi': float,
    'rlnClassNumber': int,
    'rlnLogLikeliContribution': float,
    'rlnRandomSubset': int,
    'rlnParticleName': str,
    'rlnOriginalParticleName': str,
    'rlnNrOfSignificantSamples': float,
    'rlnNrOfFrames': int,
    'rlnMaxValueProbDistribution': float,
    'rlnIndex': str,
    'rlnSubtomoIndex': str,
    'rlnMaskDensityPercentage': float,
    'rlnMaskStdPercentage': float,
    'rlnMaskBoundary': str
}

class Label():
    def __init__(self, labelName):
        self.name = labelName
        self.type = LABELS.get(labelName, str)

    def __str__(self):
        return self.name

    def __cmp__(self, other):
        return self.name == str(other)


class Item():
    """
    General class to store data from a row. (e.g. Particle, Micrograph, etc)
    """

    def copyValues(self, other, *labels):
        """
        Copy the values form other object.
        """
        for l in labels:
            setattr(self, l, getattr(other, l))

    def clone(self):
        return copy.deepcopy(self)

class MetaData():
    """ Class to parse Relion star files
    """
    def __init__(self, input_star=None):
        if input_star:
            self.read(input_star)
        else:
            self.clear()

    def clear(self):
        self._labels = OrderedDict()
        self._data = []

    def _setItemValue(self, item, label, value):
        setattr(item, label.name, label.type(value))

    def _addLabel(self, labelName):
        self._labels[labelName] = Label(labelName)

    def read(self, input_star):
        self.clear()
        found_label = False
        f = open(input_star)

        for line in f:
            values = line.strip().split()

            if not values: # empty lines
                continue

            if values[0].startswith('_rln'):  # Label line
                # Skip leading underscore in label name
                self._addLabel(labelName=values[0][1:])
                found_label = True

            elif found_label:  # Read data lines after at least one label
                # Iterate in pairs (zipping) over labels and values in the row
                item = Item()
                # Dynamically set values, using label type (str by default)
                for label, value in zip(self._labels.values(), values):
                    self._setItemValue(item, label, value)

                self._data.append(item)

        f.close()

    def _write(self, output_file):
        output_file.write("\ndata_\n\nloop_\n")
        line_format = ""

        # Write labels and prepare the line format for rows
        for i, l in enumerate(self._labels.values()):
            output_file.write("_%s #%d \n" % (l.name, i+1))
            # Retrieve the type of the label
            t = l.type
            if t is float:
                line_format += "%%(%s)f \t" % l.name
            elif t is int:
                line_format += "%%(%s)d \t" % l.name
            else:
                line_format += "%%(%s)s \t" % l.name

        line_format += '\n'

        for item in self._data:
            output_file.write(line_format % item.__dict__)

        output_file.write('\n')

    def write(self, output_star):
        try:
            output_file = open(output_star, 'w')
            self._write(output_file)
            output_file.close()
        except:
            pass

    def printStar(self):
        self._write(sys.stdout)

    def size(self):
        return len(self._data)

    def __len__(self):
        return self.size()

    def __iter__(self):
        for item in self._data:
            yield item

    def getLabels(self):
        return [l.name for l in self._labels.values()]

    def setLabels(self, **kwargs):
        """ Add (or set) labels with a given value. """
        for key, value in kwargs.iteritems():
            if key not in self._labels:
                self._addLabel(labelName=key)

        for item in self._data:
            for key, value in kwargs.iteritems():
                self._setItemValue(item, self._labels[key], value)

    def _iterLabels(self, labels):
        """ Just a small trick to accept normal lists or *args
        """
        for l1 in labels:
            if isinstance(l1, list):
                for l2 in l1:
                    yield l2
            else:
                yield l1

    def addLabels(self, *labels):
        """
        Register labes in the metadata, but not add the values to the rows
        """
        for l in self._iterLabels(labels):
            if l not in self._labels.keys():
                self._addLabel(l)

    def removeLabels(self, *labels):
        for l in self._iterLabels(labels):
            if l in self._labels:
                del self._labels[l]

    def addItem(self, item):
        """ Add a new item to the MetaData. """
        self._data.append(item)

    def setData(self, data):
        """ Set internal data with new items. """
        self._data = data

    def addData(self, data):
        """ Add new items to internal data. """
        for item in data:
            self.addItem(item)


rotation_list = [(((0,1),1),((1,2),0)), (((0,1),1),((1,2),1)), (((0,2),1),((1,2),0)), (((0,2),1),((1,2),1)), 
                (((0,1),1),((1,2),2)), (((0,1),1),((1,2),3)), (((0,2),1),((1,2),2)), (((0,2),1),((1,2),3)), 
                (((0,1),3),((1,2),0)), (((0,1),3),((1,2),1)), (((0,2),3),((1,2),0)), (((0,2),3),((1,2),1)), 
                (((0,1),3),((1,2),2)), (((0,1),3),((1,2),3)), (((0,2),3),((1,2),2)), (((0,2),3),((1,2),3)),
                (((1,2),1),((0,2),0)), (((1,2),1),((0,2),2)), (((1,2),3),((0,2),0)), (((1,2),3),((0,2),2))]