import sys
from collections import namedtuple
import csv
import glob
import os
import pycrfsuite

specialCharacter = "!@#$%^*()_+~}{|:><?;-+"

def get_utterances_from_file(dialog_csv_file, dialog_csv_filename):
    """Returns a list of DialogUtterances from an open file."""
    reader = csv.DictReader(dialog_csv_file)
    path = dialog_csv_filename.split("\\")
    return [_dict_to_dialog_utterance(du_dict, path[-1]) for du_dict in reader]

def get_utterances_from_filename(dialog_csv_filename):
    """Returns a list of DialogUtterances from an unopened filename."""
    with open(dialog_csv_filename, "r") as dialog_csv_file:
        return get_utterances_from_file(dialog_csv_file, dialog_csv_filename)

def get_data(data_dir):
    """Generates lists of utterances from each dialog file.

    To get a list of all dialogs call list(get_data(data_dir)).
    data_dir - a dir with csv files containing dialogs"""
    dialog_filenames = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    for dialog_filename in dialog_filenames:
        yield get_utterances_from_filename(dialog_filename)

DialogUtterance = namedtuple("DialogUtterance", ("act_tag", "speaker", "pos", "text", "fileName"))

PosTag = namedtuple("PosTag", ("token", "pos"))

def _dict_to_dialog_utterance(du_dict, dialog_csv_filename):
    """Private method for converting a dict to a DialogUtterance."""

    # Remove anything with
    for k, v in du_dict.items():
        if len(v.strip()) == 0:
            du_dict[k] = None

    # Extract tokens and POS tags
    if du_dict["pos"]:
        du_dict["pos"] = [
            PosTag(*token_pos_pair.split("/"))
            for token_pos_pair in du_dict["pos"].split()]
    du_dict["fileName"] = dialog_csv_filename
    return DialogUtterance(**du_dict)

def createFeatureList(files, type):
    xTrain = []
    yTrain = []
    fileNames = []
    for utterances in files:
        file = []
        labels = []
        first = True
        speaker = ''
        previous_label = ''
        for dialogUtterance in utterances:
            fileName = dialogUtterance.fileName
            feature = []
            labels.append(dialogUtterance.act_tag)
            if first:
                feature.append('1')
                feature.append('0')
                speaker = dialogUtterance.speaker
                first = False
            else:
                feature.append('0')
                if dialogUtterance.speaker == speaker:
                    feature.append('0')
                else:
                    feature.append('1')
                    speaker = dialogUtterance.speaker
            specialCharcterFlag = '0'
            if dialogUtterance.pos:
                for posTag in dialogUtterance.pos:
                    feature.append("TOKEN_"+posTag.token)
                    #feature.append(str(len(posTag.token)))
                    if posTag.token in specialCharacter:
                        specialCharcterFlag = '1'
                for posTag in dialogUtterance.pos:
                    feature.append("POS_"+posTag.pos)
            words = dialogUtterance.text.split();
            for word in words:
                feature.append(word.lower())

            #if type == 1:
            #    feature.append(previous_label)
            previous_label = dialogUtterance.act_tag
            #feature.append(specialCharcterFlag)
            file.append(feature)
        xTrain.append(file)
        yTrain.append(labels)
        fileNames.append(fileName)
    return xTrain, yTrain, fileNames


print ('Argument count : ', len(sys.argv))
#exit if file name is not provided as command line argument
if len(sys.argv) != 4:
    print ('Please send file name as command line argument')
    exit(0)

trainDir = sys.argv[1]
devDir = sys.argv[2]
outputFile = sys.argv[3]

print ('trainDir : ', trainDir, ' devDir : ', devDir,' outputFile : ', outputFile)

# get all utterances
files_train = get_data(trainDir)
files_test = get_data(devDir)

# create feature list
xTrain, yTrain, filenames_train = createFeatureList(files_train, 1)
xTest, yTest, filenames_test = createFeatureList(files_test, 2)

# train crf model
trainer = pycrfsuite.Trainer(verbose=False)

for xseq, yseq in zip(xTrain, yTrain):
    trainer.append(xseq, yseq)

trainer.set_params({
    'c1': 1.0,   # coefficient for L1 penalty
    'c2': 1e-3,  # coefficient for L2 penalty
    'max_iterations': 100,  # stop earlier

    # include transitions that are possible, but not observed
    'feature.possible_transitions': True
})

trainer.params()
trainer.train('baseline_model.crfsuite')

# test on dev data
tagger = pycrfsuite.Tagger()
tagger.open('baseline_model.crfsuite')

yPred = [tagger.tag(xseq) for xseq in xTest]

# yPred = []
# y = ['']
# for xseq in xTest:
#     list = []
#     for feature in xseq:
#         feature.append(y[0])
#         y = tagger.tag([feature])
#         list.append(y[0])
#     yPred.append(list)
#
#print(yPred[0])


correctCount = 0
count = 0
# write output file
fileHandler = open(outputFile, "w")
for i in range(0, len(yPred)):
    fileHandler.write("Filename=\""+filenames_test[i]+"\"\n")
    for j in range (0, len(yPred[i])):
        fileHandler.write(yPred[i][j]+"\n")
        if yPred[i][j] == yTest[i][j]:
            correctCount += 1
        count += 1
    fileHandler.write("\n")
fileHandler.close()

#print(correctCount)
#print(len(yTest))
print(correctCount/count)