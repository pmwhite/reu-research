import deanon
import experiment
import pickle
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt

plt.ion()

def main1():
    data = pickle.load(open('./funfun/3_hop_cbmeeks_attack.pickle', 'rb'))
    precision_points = []
    recall_points = []
    f_measure_points = []
    for cluster_size in range(1, 100):
        print(cluster_size)
        total_precision = 0
        total_recall = 0
        iterations = 10
        def deanonymizer(attacker_data):
            return deanon.pairwise_metric_best_n_match(attacker_data, deanon.jaccard_metric, 10)
        for _ in range(iterations):
            exper = experiment.concentrated_random_partition(data, 100, cluster_size / 100)
            (precision, recall) = experiment.analyze(exper, deanonymizer)
            total_precision += precision
            total_recall += recall
        ave_precision = total_precision / iterations
        ave_recall = total_recall / iterations
        precision_points.append(ave_precision)
        recall_points.append(ave_recall)
    plt.plot(precision_points, 'b')
    plt.plot(recall_points, 'r')
    plt.plot(f_measure_points, 'g')

def main2():
    for x in range(20):
        print(x)
        known_percentage = x / 20
        total_precision = 0
        total_recall = 0
        iterations = 50
        for _ in range(iterations):
            (solutions, predictions) = deanon.jaccard_threshold_predictor_experiment(attacker_data, known_percentage, 0.01)
            (precision, recall) = deanon.evaluate(predictions, solutions)
            total_precision += precision
            total_recall += recall
        ave_precision = total_precision / iterations
        ave_recall = total_recall / iterations
        precision_points.append(ave_precision)
        recall_points.append(ave_recall)
        f_measure_points.append(2 * ave_recall * ave_precision / (ave_recall + ave_precision))

def main3():
    data = pickle.load(open('./funfun/3_hop_cbmeeks_attack.pickle', 'rb'))
    precision_points = []
    recall_points = []
    f_measure_points = []
    x_stops = list(range(1, 100))
    for cluster_size in x_stops:
        print(cluster_size)
        total_precision = 0
        total_recall = 0
        iterations = 100
        def deanonymizer(attacker_data):
            return deanon.pairwise_metric_greedy(attacker_data, deanon.jaccard_location_metric, 1.01)
        for _ in range(iterations):
            exper = experiment.concentrated_random_partition(data, 100, cluster_size / 100)
            (precision, recall) = experiment.analyze(exper, deanonymizer)
            total_precision += precision
            total_recall += recall
        ave_precision = total_precision / iterations
        ave_recall = total_recall / iterations
        precision_points.append(ave_precision)
        recall_points.append(ave_recall)
    plt.ylim([0,1])
    plt.xlabel('Percentage users known')
    plt.plot(x_stops, precision_points, 'b', label='precision')
    plt.plot(x_stops, recall_points, 'r', label='recall')
    plt.legend()

def main4():
    data = pickle.load(open('./funfun/3_hop_cbmeeks_attack.pickle', 'rb'))
    p_xs = []
    p_ys = []
    n_xs = []
    n_ys = []
    for i in range(1):
        print(i)
        exper = experiment.concentrated_random_partition(data, 100, 0.10)
        (p_series, n_series) = experiment.analyze_metric(exper, deanon.jaccard_metric, deanon.location_metric)
        p_unzipped = list(zip(*p_series))
        n_unzipped = list(zip(*n_series))
        p_xs.extend(p_unzipped[0])
        p_ys.extend(p_unzipped[1])
        n_xs.extend(n_unzipped[0])
        n_ys.extend(n_unzipped[1])
    plt.xlabel('Edge set similarity')
    plt.ylabel('Location similarity')
    plt.scatter(n_xs, n_ys, color='black', s=3)
    plt.scatter(p_xs, p_ys, color='red', s=10)

main3()