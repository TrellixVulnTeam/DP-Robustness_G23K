## test_attack.py -- sample code to test attack procedure
##
## Copyright (C) 2016, Nicholas Carlini <nicholas@carlini.com>.
##
## This program is licenced under the BSD 2-Clause licence,
## contained in the LICENCE file in this directory.

import sys
import time
import json

import numpy as np
import pandas as pd
import tensorflow as tf

from Model import Model
from third_party.carlini.l2_attack_orig import CarliniL2
from third_party.carlini.setup_mnist import MNIST

def generate_data(data, samples, targeted=True, start=0, inception=False):
    """
    Generate the input data to the attack algorithm.

    data: the images to attack
    samples: number of samples to use
    targeted: if true, construct targeted attacks, otherwise untargeted attacks
    start: offset into data to use
    inception: if targeted and inception, randomly sample 100 targets intead of 1000
    """
    inputs = []
    targets = []
    for i in range(samples):
        if targeted:
            if inception:
                seq = random.sample(range(1, 1001), 10)
            else:
                seq = range(data.test_labels.shape[1])

            for j in seq:
                if (j == np.argmax(data.test_labels[start + i])) and (inception == False):
                    continue
                inputs.append(data.test_data[start + i])
                targets.append(np.eye(data.test_labels.shape[1])[j])
        else:
            # inputs.append(tf.convert_to_tensor(data.test_data[start + i]))
            inputs.append(data.test_data[start + i])
            targets.append(data.test_labels[start + i])

    inputs = np.array(inputs)
    targets = np.array(targets)

    return inputs, targets

if __name__ == "__main__":

    resultsDF = {}
    eps = sys.argv[1]
    num_samples = int(sys.argv[2])

    with tf.Session() as sess:
        init_op = tf.group(tf.global_variables_initializer(), tf.local_variables_initializer())
        _ = sess.run([init_op])

        print("EPSILON = %s" % eps)
        resultsDict = {}
        modelPath = "trained_models/ndppca_eps_%s_600_amortized" % eps
        data, model = MNIST(), Model(modelPath) 
        inputs, targets = generate_data(data, samples=num_samples, targeted=True,
                                        start=0, inception=False)

        plc = tf.placeholder_with_default(tf.zeros((1, 28, 28, 1), dtype=tf.float32), shape=(None, 28, 28, 1))
        mnist_output = model.predict(plc)

        def run_model(the_inputs):
            the_inputs = the_inputs.reshape((-1, 28, 28, 1))
            output = sess.run([mnist_output], feed_dict={plc: the_inputs})
            return output

        attack = CarliniL2(sess, model, max_iterations=1000, confidence=0)
        adv = attack.attack(inputs, targets, model)

        # None adversarial examples for each sample of MNIST. 
        for sample in range(int(len(adv) / 9)):
            # Initialize resultsDict to be indexed by sample #
            resultsDict[sample] = {}

            validOutput = run_model(inputs[sample * 9])
            resultsDict[sample]["Valid Eps %s Classification" % eps] = np.argmax(validOutput[0][0])
            resultsDict[sample]["Valid Eps %s Vector" % eps] = validOutput[0]

            for example in range(9):
                prefix = "Adv%d Eps %s " % (example, eps)
                index = sample * 9 + example

                adv_tensor = adv[index : index + 1][0].astype(np.float32)
                advOutput = run_model(adv_tensor)
                resultsDict[sample][prefix + "Classification"] = np.argmax(advOutput[0][0])
                resultsDict[sample][prefix + "Vector"] = advOutput[0]
                resultsDict[sample][prefix + "Distortion"] = np.sum((adv[index] - inputs[index]) ** 2) ** .5

        resultsDF = pd.DataFrame.from_dict(resultsDict, orient='index')
        print(resultsDF)
        saveFile = "results/sample%d/no_pca_eps_%s_600_amortized.json" % (num_samples, eps)
        resultsDF.to_json(path_or_buf=saveFile)
    sess.close()
