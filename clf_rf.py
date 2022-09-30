import numpy as np
import matplotlib.pyplot as plt
import json
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, f1_score
from utils import plot_cm, calcualte_classification_report
import pickle
import datetime
import os

plt.ion()

# TO DO: Implement simple CV procedure (5-fold) 
# Hyperopt for hyperparameter optimization did not work well for this dataset.
def baseline_model(train_data_f, test_data_file, output_dir, cv_cross_val=False, save=False):
    """Baseline model for predicting ECM from EIS data
    Linear classifiers perform poorly on this dataset, so we use a RF classifier (non-linear)
    Hyperparameter optimization with hpsklearn, keeping it simple for the baseline model
    Parameters
    ----------
    train_data_f : str
        Path to training data file
    test_data_file : str
        Path to test data file
    output_dir : str
        Path to output directory
    cv_cross_val : bool
        Perform cross validation
    save : bool
        Save figures
        
    Returns
    -------
    acc_test : float
        Test accuracy
    acc_train : float
        Train accuracy
    """
    # Load data
    train_data = np.loadtxt(train_data_f, delimiter=",")
    test_data = np.loadtxt(test_data_file, delimiter=",")

    # Preprocess data
    X_train = train_data[:,0:-1]
    y_train = train_data[:,-1].ravel()
    X_test = test_data[:,0:-1]
    y_test = test_data[:,-1].ravel()
    # Standardize data using sklearn standard scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    if cv_cross_val:
        # Use sklearn 5 fold CV to determine the number of estimators
        # Loop through all possibilities
        n_estimators = [10, 50, 100, 150, 200, 500, 800, 1000]
        f1 = []
        f1_std = []
        folds = 5 
        for nb in n_estimators:
            print(f"CV with number of estimators: {nb}")
            clf = RandomForestClassifier(
                class_weight='balanced_subsample', n_estimators=nb, n_jobs=-1, random_state=42)
                            
            # Cross-validation: Predict the test samples based on a predictor that was trained with the 
            # remaining data. Repeat until prediction of each sample is obtained.
            # (Only one prediction per sample is allowed)
            # Only these two cv methods work. Reson: Each sample can only belong to EXACTLY one test set. 
            # Other methods of cross validation might violate this constraint
            # For more information see: 
            # https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_predict.html
            scores = cross_val_score(clf, X_train_scaled, y_train, cv=folds, n_jobs=-1, scoring='f1_macro')
            f1.append(scores.mean())
            f1_std.append(scores.std())
        # Pick the best number of estimators based on the one standard deviation rule
        best_nb = n_estimators[np.argmax(f1)]
        f1_max_loc = np.argmax(f1)
        filtered_lst = [(i, element) for i,element in enumerate(f1) if element > f1[f1_max_loc]-(1*f1_std[f1_max_loc])]
        f1_std_max_loc, _ = min(filtered_lst)
        best_nb_std = n_estimators[f1_std_max_loc]
        print("Best number of estimators: {}".format(best_nb))
        print("Best number of estimators (1std), selected to proceed: {}".format(best_nb_std))
        clf = RandomForestClassifier(
            class_weight='balanced_subsample', n_estimators=best_nb_std, n_jobs=-1, random_state=42)
        clf.fit(X_train_scaled, y_train)
    else: 
        # Random Forest Classifier with hyperparamters from previous hyperparameter optimization run
        # New runs might give slightly different results
        clf = RandomForestClassifier(
            class_weight='balanced_subsample', n_estimators=50, n_jobs=-1, random_state=42)
        
        clf.fit(X_train_scaled, y_train)
    
    y_test_pred = clf.predict(X_test_scaled)
    y_train_pred = clf.predict(X_train_scaled)
    
    with open('data/le_name_mapping.json', 'r') as f:
        mapping = json.load(f)
        le = LabelEncoder()
    mapping['classes'] = [mapping[str(int(i))] for i in range(9)]
    le.classes_ = np.array(mapping['classes'])
    plot_cm(y_test, y_test_pred, le, save=save, figname=f'{output_dir}/cm_rfb_test')
    plot_cm(y_train, y_train_pred, le, save=save, figname=f'{output_dir}/cm_rfb_train')
    plt.show()

    # Save model
    with open(f"{output_dir}/rf.pkl", 'wb') as f:
        pickle.dump(clf, f)

    # Calculate f1 and save classification report
    calcualte_classification_report(y_train, y_train_pred, y_test, y_test_pred, le, save=save, output_dir=output_dir)

    return 


if __name__ == "__main__":
    train_data_f = "data/train_data_inter.csv"
    test_data_f = "data/test_data_inter.csv"

    # Create new folder with results, name is datetime
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = f"results/clf/rf/{now_str}"
    os.mkdir(output_dir)

    baseline_model(train_data_f, test_data_f, output_dir, cv_cross_val=False, save=True)
    print('Done')

    #accs_umap = baseline_model()
    #print(f'Accuracie UMAP data: {accs_umap}')