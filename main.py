## test_attack.py -- sample code to test attack procedure
##
## Copyright (C) 2016, Nicholas Carlini <nicholas@carlini.com>.
##
## This program is licenced under the BSD 2-Clause licence,
## contained in the LICENCE file in this directory.

import time

import numpy as np
import tensorflow as tf

from Model import Model
from third_party.carlini.l2_attack_orig import CarliniL2
# from third_party.carlini.setup_cifar import CIFAR, CIFARModel
from third_party.carlini.setup_mnist import MNIST


# from third_party.carlini.setup_inception import ImageNet, InceptionModel


def show(img):
    """
    Show MNSIT digits in the console.
    """
    remap = "  .*#" + "#" * 100
    img = (img.flatten() + .5) * 3
    if len(img) != 784: return
    print("START")
    for i in range(28):
        print("".join([remap[int(round(x))] for x in img[i * 28:i * 28 + 28]]))


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

    with tf.Session() as sess:

        init_op = tf.group(tf.global_variables_initializer(), tf.local_variables_initializer())
        _ = sess.run([init_op])
        #data, model = MNIST(), Model("trained_models/jl_eps_0_100_amortized") #Model("trained/dp_mnist")
        data, model = MNIST(), Model("trained_models/ndppca_eps_0_600_amortized") #Model("trained/dp_mnist")
        
        inputs, targets = generate_data(data, samples=1, targeted=True,
                                        start=0, inception=False)

        plc = tf.placeholder_with_default(tf.zeros((1, 28, 28, 1), dtype=tf.float32), shape=(None, 28, 28, 1))

        mnist_output = model.predict(plc)

        def run_model(the_inputs):
            the_inputs = the_inputs.reshape((-1, 28, 28, 1))
            output = sess.run([mnist_output], feed_dict={plc: the_inputs})
            print(' Output vector:', output[0])
            print('Classification:', np.argmax(output[0][0]))
            return output

        run_model(inputs)

        attack = CarliniL2(sess, model, max_iterations=1000, confidence=0)
        timestart = time.time()
        adv = attack.attack(inputs, targets, model)
        timeend = time.time()

        print("Took", timeend - timestart, "seconds to run", len(inputs), "samples.")

        for i in range(len(adv)):
            print("Valid:")
            show(inputs[i])
            run_model(inputs[i])

            print("Adversarial:")
            show(adv[i])
            adv_tensor = adv[i:i + 1][0].astype(np.float32)
            run_model(adv_tensor)
            print("Total distortion:", np.sum((adv[i] - inputs[i]) ** 2) ** .5)

