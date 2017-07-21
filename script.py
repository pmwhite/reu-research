import deanon
import experiment
import pickle
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt

plt.ion()

data = pickle.load(open('./funfun/3_hop_cbmeeks_attack.pickle', 'rb'))

precision_points = []
recall_points = []
f_measure_points = []
# for x in range(20):
#     print(x)
#     known_percentage = x / 20
#     total_precision = 0
#     total_recall = 0
#     iterations = 50
#     for _ in range(iterations):
#         (solutions, predictions) = deanon.jaccard_threshold_predictor_experiment(attacker_data, known_percentage, 0.01)
#         (precision, recall) = deanon.evaluate(predictions, solutions)
#         total_precision += precision
#         total_recall += recall
#     ave_precision = total_precision / iterations
#     ave_recall = total_recall / iterations
#     precision_points.append(ave_precision)
#     recall_points.append(ave_recall)
#     f_measure_points.append(2 * ave_recall * ave_precision / (ave_recall + ave_precision))
    
for cluster_size in range(1, 30):
    print(cluster_size)
    exper = experiment.cluster_partition(data, cluster_size)
    def deanonymizer(attacker_data):
        predictions = list(deanon.jaccard_simple(attacker_data, 0.01))
        solutions = exper.solutions
        # for prediction in predictions:
            # if prediction[2] == True:
                # print(prediction)
        # for solution in solutions:
            # if solution[2] == True:
                # print(solution)
        return predictions

    (precision, recall) = experiment.analyze(exper, deanonymizer)
    print(precision, recall)
    precision_points.append(precision)
    recall_points.append(recall)
    # f_measure_points.append(2 * recall * precision / (recall + precision))

plt.plot(precision_points, 'b')
plt.plot(recall_points, 'r')
plt.plot(f_measure_points, 'g')
