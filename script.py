"Scripts for running analysis on datasets. These can be used as examples, but
some of them may be broken through not being run in a while."
import deanon
import common
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
    x_stops = list(range(1, 100, 5))
    for cluster_size in x_stops:
        print(cluster_size)
        total_precision = 0
        total_recall = 0
        iterations = 1
        def deanonymizer(attacker_data):
            return deanon.pairwise_metric_greedy(attacker_data, common.tg_activity_metric, 0.90)
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
    plt.plot(x_stops, precision_points, '-', color='black', label='precision')
    plt.plot(x_stops, recall_points, '--', color='black', label='recall')
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
        (p_series, n_series) = experiment.analyze_metric(exper, deanon.jaccard_metric, common.tg_location_metric)
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

def main5():
    data = pickle.load(open('./funfun/3_hop_cbmeeks_attack.pickle', 'rb'))
    p_xs = []
    p_ys = []
    n_xs = []
    n_ys = []
    for i in range(5):
        print(i)
        exper = experiment.concentrated_random_partition(data, 100, 0.90)
        (p_series, n_series) = experiment.analyze_metrics(exper, deanon.cosine_jaccard_metric, deanon.jaccard_metric)
        p_unzipped = list(zip(*p_series))
        n_unzipped = list(zip(*n_series))
        print(len(p_unzipped))
        print(len(n_unzipped))
        p_xs.extend(p_unzipped[0])
        p_ys.extend(p_unzipped[1])
        n_xs.extend(n_unzipped[0])
        n_ys.extend(n_unzipped[1])
    plt.scatter(n_xs, n_ys, color='black', s=3)
    plt.scatter(p_xs, p_ys, color='red', s=10)

def main6():
    data = pickle.load(open('./funfun/3_hop_cbmeeks_attack.pickle', 'rb'))
    precision_points = []
    recall_points = []
    f_measure_points = []
    x_stops = list(range(1, 100, 5))
    for cluster_size in x_stops:
        print(cluster_size)
        total_precision = 0
        total_recall = 0
        iterations = 50
        def deanonymizer(attacker_data):
            pred1 = deanon.pairwise_metric_conservative(attacker_data, common.tg_location_metric, 0.99)
            pred2 = deanon.pairwise_metric_simple_threshold(attacker_data, deanon.cosine_jaccard_metric, 0.1)
            return set(pred1).intersection(pred2)
        for _ in range(iterations):
            exper = experiment.concentrated_random_partition(data, 50, cluster_size / 100)
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

def main7():
    data = pickle.load(open('./funfun/3_hop_cbmeeks_attack.pickle', 'rb'))
    p_xs = []
    p_ys = []
    n_xs = []
    n_ys = []
    for i in range(6):
        print(i)
        exper = experiment.concentrated_random_partition(data, 30, 0.30)
        (p_series, n_series) = experiment.analyze_rows(exper, deanon.jaccard_metric)
        p_unzipped = list(zip(*p_series))
        n_unzipped = list(zip(*n_series))
        p_xs.extend(p_unzipped[0])
        p_ys.extend(p_unzipped[1])
        n_xs.extend(n_unzipped[0])
        n_ys.extend(n_unzipped[1])
    plt.scatter(n_ys, n_xs, marker='o', facecolors='none', edgecolors='black', s=10)
    plt.scatter(p_ys, p_xs, marker='o', color='black', s=10)

def main8():
    data = pickle.load(open('./funfun/3_hop_cbmeeks_attack.pickle', 'rb'))
    precision_points = []
    recall_points = []
    f_measure_points = []
    x_stops = list(range(3, 100))
    for cluster_size in x_stops:
        print(cluster_size)
        total_precision = 0
        total_recall = 0
        iterations =1 
        def deanonymizer(attacker_data):
            pred1 = deanon.metric_eccentricity_greedy(attacker_data, common.tg_activity_metric, 0.5)
            return set(pred1)
        for _ in range(iterations):
            exper = experiment.concentrated_random_partition(data, cluster_size, 0)
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

# Decide which main program we want to run.
main3()
