from sklearn.metrics import accuracy_score, f1_score

def evaluate(predictions, labels):
    acc = accuracy_score(labels, predictions)
    macro_f1 = f1_score(labels, predictions, average='macro')
    return acc, macro_f1