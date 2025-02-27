import torch
import torch.nn as nn
import torchaudio
import numpy as np
import pickle
import torch.nn.functional as F
import torch.optim as optim
import random
import librosa
import matplotlib.pyplot as plt


# torch.set_printoptions(threshold=1000000)
# CONSTANTS
LSTM_INPUT_SIZE = 128     # Input dim of LSTM_input
HIDDEN_DIM = 256
SEQ_LEN = 20            # Define how many numbers to describe a piece of audio
OUTPUT_DIM = 20         # Will be set to 20
UPPER_FILE = 20       # how many files (up to) do we want
LR = 0.01               #learning rate
NUM_LAYERS = 3          # Underlying layers in LSTM network
NUM_EPOCHS = 500         # How many times we want to run the network, each time with random combination of dataset
#####################
# Playground
#####################
#
# y, sr = librosa.load('Training_Set/voice/p225/p225_002.wav', duration=3)
# mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=128)
# print(mfccs)
# print(len(mfccs),len(mfccs[0]))

#####################
# Load data
#####################
print('\x1b[6;30;42m' + "--------------Loading data--------------"+'\x1b[0m')
X_raw = [[] for i in range(20)]
training_set = []
speaker_list = ['p225','p228','p229','p230','p231','p233','p236','p239','p240','p244','p226','p227','p232','p243','p254','p256','p258','p259','p270','p273']
for i in range(OUTPUT_DIM):
    count = 0
    for j in range(UPPER_FILE):
        try:
            y, sr = librosa.load('Training_Set/voice/'+speaker_list[i]+'/'+speaker_list[i]+'_'+("%03d" % (20))+'.wav', duration=10)
            mfccs = librosa.feature.mfcc(y=y, sr=sr,n_mfcc=LSTM_INPUT_SIZE)
            print("Loading",j,"th audio for speaker",speaker_list[i])
            X_raw[i].append(torch.FloatTensor(mfccs))
            count+=1
        except:
            continue
    training_set.append(torch.cat(X_raw[i],dim=1))
    print("Loaded:",i+1,"/",OUTPUT_DIM,". The speaker",speaker_list[i],"has the shape:",training_set[i].size())

#####################
# Prepare data
#####################
print('\x1b[6;30;42m' + "--------------Data preparation starts--------------"+'\x1b[0m')
X_train = []
y_train = []
for i in range(OUTPUT_DIM):
    temp = torch.split(training_set[i],SEQ_LEN,dim=1)
    X_train.append(list(temp)[:-1])
    y_train.append([i]*(len(temp)-1))

X_train = sum(X_train, [])[0:2202] # list of tensors
y_train = sum(y_train, [])
BATCH_SIZE = len(X_train)
print("BATCH_SIZE is:", BATCH_SIZE)

# Now apply minibatch to the data
def batch(X_train, y_train,shuffle):
    if shuffle:
        shuffle_list = list(zip(X_train, y_train))
        random.shuffle(shuffle_list)
        X_train, y_train = zip(*shuffle_list)
    block_X = []
    block_y = []
    for j in range(BATCH_SIZE):
        block_X.append(X_train[j].t().unsqueeze(1))
        block_y.append(y_train[j])
    batch_X = torch.cat(block_X,dim=1)
    batch_y = torch.LongTensor(block_y)
    return batch_X,batch_y

#####################
# Build model
#####################
print('\x1b[6;30;42m' + "--------------building LSTM module--------------"+'\x1b[0m')

class LSTM(nn.Module):

    def __init__(self, input_dim, hidden_dim, batch_size, output_dim, num_layers):
        super(LSTM, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.batch_size = batch_size
        self.num_layers = num_layers

        # Define the LSTM layer
        self.lstm = nn.LSTM(self.input_dim, self.hidden_dim, self.num_layers)

        # Define the output layer
        self.linear = nn.Linear(self.hidden_dim, output_dim)
        self.hidden2label = nn.Linear(hidden_dim, output_dim)

    def init_hidden(self):
        # This is what we'll initialise our hidden state as
        return (torch.zeros(self.num_layers, self.batch_size, self.hidden_dim),
                torch.zeros(self.num_layers, self.batch_size, self.hidden_dim))

    def forward(self, input):
        # Forward pass through LSTM layer
        # shape of lstm_out: [input_size, batch_size, hidden_dim]
        # shape of self.hidden: (a, b), where a and b both
        # have shape (num_layers, batch_size, hidden_dim).
        lstm_out, self.hidden = self.lstm(input.view(SEQ_LEN, self.batch_size, -1))

        # Only take the output from the final timetep
        # Can pass on the entirety of lstm_out to the next layer if it is a seq2seq prediction
        y  = self.hidden2label(lstm_out[-1])
        return y

model = LSTM(LSTM_INPUT_SIZE, HIDDEN_DIM, batch_size=BATCH_SIZE, output_dim=OUTPUT_DIM, num_layers=NUM_LAYERS)
loss_fn = torch.nn.CrossEntropyLoss()
optimiser = optim.SGD(model.parameters(), lr=LR, momentum=0.9)

checkpoint = torch.load("1762.pt")
model.load_state_dict(checkpoint['model_state_dict'])
optimiser.load_state_dict(checkpoint['optimizer_state_dict'])
#####################
# Train model
#####################
print('\x1b[6;30;42m' + "--------------SANITY--------------"+'\x1b[0m')
batch_X, batch_y = batch(X_train, y_train, True)

y_pred_batch = model(batch_X)
my_result = y_pred_batch.detach().numpy()
my_label = np.argmax(my_result, axis=1)
print("my result while training",my_label)

np_batch_y = batch_y.detach().numpy()
print("ground truth is",np_batch_y)
accuracy = 0
for i in range(len(np_batch_y)):
    if np_batch_y[i] == my_label[i]:
        accuracy += 1
print("The current accuracy is:", accuracy, "/", len(np_batch_y))
