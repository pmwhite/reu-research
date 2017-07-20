import deanon
import pickle
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt

plt.ion()

attacker_data = pickle.load(open('./funfun/small/cbmeeks_attack.pickle', 'rb'))

precision_points = []
recall_points = []
f_measure_points = []
for x in range(52):
    print(x)
    known_percentage = x / 52
    total_precision = 0
    total_recall = 0
    iterations = 100
    for _ in range(iterations):
        (solutions, predictions) = deanon.jaccard_threshold_predictor_experiment(attacker_data, known_percentage, 0.03)
        (precision, recall) = deanon.evaluate(predictions, solutions)
        total_precision += precision
        total_recall += recall
    ave_precision = total_precision / iterations
    ave_recall = total_recall / iterations
    precision_points.append(ave_precision)
    recall_points.append(ave_recall)
    f_measure_points.append(2 * ave_recall * ave_precision / (ave_recall + ave_precision))
    

plt.plot(precision_points, 'b')
plt.plot(recall_points, 'r')
plt.plot(f_measure_points, 'g')
