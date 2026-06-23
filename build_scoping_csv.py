#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path


HEADER = [
    "title",
    "country",
    "year",
    "doi",
    "context",
    "problem",
    "ai_tools",
    "contribution",
    "results",
    "dataset",
    "data_modality",
    "population",
    "limitations",
    "publication_type",
]


EXCLUDE_DUPLICATE_OR_SUPPLEMENT_FILES = {
    # Exact duplicate of the named article PDF.
    "197.pdf",
    # Exact duplicate of the Cohen et al. AJOG abstract PDF.
    "PIIS0002937823015636.pdf",
    # Same article/DOI as Rocha et al. 2021; keep the author-named PDF row.
    "Data-driven risk stratification for preterm birth in Brazil a population-based study to develop of a machine learning risk assessment approach.pdf",
    # Same AJOG abstract as PIIS0002937816315381; keep the publisher-ID row because it carries the metadata title.
    "Identification of unique risk groups for preterm birth using routinely screened biomarkers and machine learning.pdf",
    # Supporting information for Synan et al. 2023, not a standalone article.
    "am3c04260_si_001.pdf",
}


TITLE_OVERRIDES = {
    "2709-0094-52-7-39011.pdf": "Development and Evaluation of a Predictive Tool for Second-Pregnancy Preterm Birth and Cervical Insufficiency in Patients With a History of Cervical Insufficiency",
    "ATDE-18-ATDE210243.pdf": "EHG-Based Preterm Delivery Prediction Algorithm Driven by Transfer Learning",
    "Abdi et al. - 2025 - Developing a prognostic model for predicting preterm birth using a machine learning algorithm.pdf": "Developing a prognostic model for predicting preterm birth using a machine learning algorithm",
    "Ahmad et al. - 2025 - Early prediction of very and extreme preterm births using a one-class classification framework on el.pdf": "Early prediction of very and extreme preterm births using a one-class classification framework on electronic health records",
    "Article à la page 6 Prediction of spontaneous preterm birth among twin gestations using machine learning and texture analysis of cervical ultrasound images.pdf": "Prediction of spontaneous preterm birth among twin gestations using machine learning and texture analysis of cervical ultrasound images",
    "Chakoory et al. - 2024 - DeepMPTB a vaginal microbiome-based deep neural network as artificial intelligence strategy for eff.pdf": "DeepMPTB: a vaginal microbiome-based deep neural network as artificial intelligence strategy for effective prediction of preterm birth",
    "Cheng et al. - 2022 - Novel Multichannel Entropy Features and Machine Learning for Early Assessment of Pregnancy Progressi.pdf": "Novel Multichannel Entropy Features and Machine Learning for Early Assessment of Pregnancy Progression Using Electrohysterography",
    "Costanzo et al. - 2025 - Prediction of preterm birth from cervical length measurements in twin pregnancies using machine lear.pdf": "Prediction of preterm birth from cervical length measurements in twin pregnancies using machine learning",
    "Dynamic-Model-for-Early-Detection-of-Preterm-Labor_2025_Institute-of-Computer-Science-IOCS.pdf": "Dynamic Model for Early Detection of Preterm Labor",
    "Greylag-Goose-Optimization-and-Deep-LearningBased-Electrohysterogram-Signal-Analysis-for-Preterm-Birth-Risk-Prediction_2025_Tech-Science-Press.pdf": "Greylag Goose Optimization and Deep Learning-Based Electrohysterogram Signal Analysis for Preterm Birth Risk Prediction",
    "Identification of unique risk groups for preterm birth using routinely screened biomarkers and machine learning.pdf": "Identification of unique risk groups for preterm birth using routinely screened biomarkers and machine learning",
    "Kloska et al. - 2025 - Predicting preterm birth using machine learning methods.pdf": "Predicting preterm birth using machine learning methods",
    "Maqsood et al. - 2026 - Comparative machine learning models for early prediction of preterm birth from maternal serum biomar.pdf": "Comparative machine learning models for early prediction of preterm birth from maternal serum biomarkers",
    "Mirzamoradi et al. - 2024 - A Neural Network-based Approach to Prediction of Preterm Birth using Non-invasive Tests.pdf": "A Neural Network-based Approach to Prediction of Preterm Birth using Non-invasive Tests",
    "Qian et al. - 2025 - Predicting the risk of preterm birth with machine learning and electronic health records in China.pdf": "Predicting the risk of preterm birth with machine learning and electronic health records in China",
    "Teng et al. - 2025 - Machine learning prediction of preterm birth in women under 35 using routine biomarkers in a retrosp.pdf": "Machine learning prediction of preterm birth in women under 35 using routine biomarkers in a retrospective study",
    "Using-an-innovative-stacked-ensemble-algorithm-for-the-accurate-prediction-of-preterm-birth_2019_Galenos-Yayincilik-infogalenoscomtr.pdf": "Using an innovative stacked ensemble algorithm for the accurate prediction of preterm birth",
    "Xiong et al. - 2025 - Machine learning-based prediction algorithm of spontaneous preterm birth using multi-source data.pdf": "Machine learning-based prediction algorithm of spontaneous preterm birth using multi-source data",
    "Zhang et al. - 2022 - The Prediction of Preterm Birth Using Time-Series Technology-Based Machine Learning Retrospective C.pdf": "The Prediction of Preterm Birth Using Time-Series Technology-Based Machine Learning: Retrospective Cohort Study",
    "am3c04260_si_001.pdf": "Supporting Information: First Trimester Prediction of Preterm Birth in Patient Plasma with Machine-Learning-Guided Raman Spectroscopy and Metabolomics",
    "jogh-13-04051.pdf": "Development of risk prediction models for preterm delivery in a rural setting in Ethiopia",
}


DOI_OVERRIDES = {
    "Dynamic-Model-for-Early-Detection-of-Preterm-Labor_2025_Institute-of-Computer-Science-IOCS.pdf": "",
    "Hornaday et al. - 2025 - Machine learning for the prediction of spontaneous preterm birth using early second and third trimes.pdf": "10.1371/journal.pone.0310937",
    "Khan et al. - 2023 - Predicting preterm birth using explainable machine learning in a prospective cohort of nulliparous a.pdf": "10.1371/journal.pone.0293925",
    "Data-driven risk stratification for preterm birth in Brazil a population-based study to develop of a machine learning risk assessment approach.pdf": "10.1016/j.lana.2021.100053",
    "Rocha et al. - 2021 - Data-driven risk stratification for preterm birth in Brazil a population-based study to develop of.pdf": "10.1016/j.lana.2021.100053",
    "Article à la page 6 Prediction of spontaneous preterm birth among twin gestations using machine learning and texture analysis of cervical ultrasound images.pdf": "",
    "am3c04260_si_001.pdf": "10.1021/acsami.3c04260",
}


YEAR_OVERRIDES = {
    "197.pdf": "not reported",
    "Machine Learning Approach for Preterm Birth Prediction Based on Maternal Chronic Conditions.pdf": "not reported",
    "A-novel-sequencebased-transformer-model-architecture-for-integrating-multiomics-data-in-preterm-birth-risk-prediction_2025_Nature-Research.pdf": "2025",
    "A_Preterm_Birth_Risk_Prediction_System_for_Mobile_Health_Applications_Based_on_the_Support_Vector_Machine_Algorithm.pdf": "2018",
    "Application of machine-learning to predict early spontaneous preterm birth among nulliparous non-Hispanic black and white women.pdf": "2019",
    "Article à la page 6 Prediction of spontaneous preterm birth among twin gestations using machine learning and texture analysis of cervical ultrasound images.pdf": "2019",
    "Cohen et al. - 2024 - 736 Identifying women at high risk for preterm birth based on clinical data using machine learning.pdf": "2024",
    "PIIS0002937823015636.pdf": "2024",
    "Identification of unique risk groups for preterm birth using routinely screened biomarkers and machine learning.pdf": "2017",
    "PIIS0002937816315381.pdf": "2017",
    "PIIS0002937822011279.pdf": "2023",
    "Preterm_Birth_Prediction_by_Classification_of_Spectral_Features_of_Electrohysterography_Signals_using_1D_Convolutional_Neural_Network_Preliminary_Results.pdf": "2023",
    "Utilizing_Deep_Learning_and_Genome_Wide_Association_Studies_for_Epistatic-Driven_Preterm_Birth_Classification_in_African-American_Women.pdf": "2020",
    "am3c04260_si_001.pdf": "2023",
    "diagnostics-16-00499.pdf": "2026",
}


COUNTRY_OVERRIDES = {
    "1-s2.0-S0169260725005966-main.pdf": "Colombia",
    "1-s2.0-S1532046419302539-main.pdf": "United States",
    "1-s2.0-S2352914822001927-main.pdf": "United States",
    "197.pdf": "India",
    "2709-0094-52-7-39011.pdf": "China",
    "A-novel-sequencebased-transformer-model-architecture-for-integrating-multiomics-data-in-preterm-birth-risk-prediction_2025_Nature-Research.pdf": "China",
    "ATDE-18-ATDE210243.pdf": "China; public EHG database",
    "A_Meta-learner_Based_Ensemble_System_of_Neural_Networks_for_Improving_the_Accuracy_of_Preterm_Birth_Prediction.pdf": "India",
    "A_Preterm_Birth_Risk_Prediction_System_for_Mobile_Health_Applications_Based_on_the_Support_Vector_Machine_Algorithm.pdf": "Not specified; multi-country author team",
    "Abdi et al. - 2025 - Developing a prognostic model for predicting preterm birth using a machine learning algorithm.pdf": "Iran",
    "Abraham et al. - 2022 - Dense phenotyping from electronic health records enables machine learning-based prediction of preter.pdf": "United States",
    "Ahmad et al. - 2025 - Early prediction of very and extreme preterm births using a one-class classification framework on el.pdf": "United Arab Emirates",
    "Al Ghadban et al. - 2024 - Prediction of spontaneous preterm birth using supervised machine learning on metabolomic data A cas.pdf": "United Kingdom",
    "AlSaad et al. - 2022 - PredictPTB an interpretable preterm birth prediction model using attention-based recurrent neural n.pdf": "Not specified; large EHR cohort",
    "Application of machine-learning to predict early spontaneous preterm birth among nulliparous non-Hispanic black and white women.pdf": "United States",
    "Article à la page 6 Prediction of spontaneous preterm birth among twin gestations using machine learning and texture analysis of cervical ultrasound images.pdf": "Canada",
    "Barnova et al. - 2025 - Predictive Obstetrics Electrohysterogram-Based Detection of Preterm Labor.pdf": "Czechia; public EHG database",
    "Belaghi - 2024 - Prediction of preterm birth in multiparous women using logistic regression and machine learning appr.pdf": "Canada",
    "Cervical texture analysis in mid-trimester scan to predict spontaneous preterm birth A case-control study.pdf": "Spain",
    "Cervix_Ultrasound_Texture_Analysis_to_Differentiate_Between_Term_and_Preterm_Birth_Pregnancy_A_Machine_Learning_Approach.pdf": "United States",
    "Chakoory et al. - 2024 - DeepMPTB a vaginal microbiome-based deep neural network as artificial intelligence strategy for eff.pdf": "France; multi-cohort vaginal microbiome data",
    "Chen et al. - 2024 - Development and validation of a spontaneous preterm birth risk prediction algorithm based on materna.pdf": "China",
    "Cheng et al. - 2022 - Novel Multichannel Entropy Features and Machine Learning for Early Assessment of Pregnancy Progressi.pdf": "China/Netherlands; annotated EHG database",
    "Cohen et al. - 2024 - 736 Identifying women at high risk for preterm birth based on clinical data using machine learning.pdf": "Israel",
    "Comparative_Analysis_of_Different_ML_Models_Towards_Term_and_Pre-Term_Classification.pdf": "India; public EHG database",
    "Computational and Mathematical Methods in Medicine - 2017 - Chen - Feature Extraction and Classification of EHG between.pdf": "China; public EHG database",
    "Costanzo et al. - 2025 - Prediction of preterm birth from cervical length measurements in twin pregnancies using machine lear.pdf": "Canada",
    "Data-driven risk stratification for preterm birth in Brazil a population-based study to develop of a machine learning risk assessment approach.pdf": "Brazil",
    "Ding et al. - 2024 - Prediction of preterm birth using machine learning a comprehensive analysis based on large-scale pr.pdf": "China",
    "Dynamic-Model-for-Early-Detection-of-Preterm-Labor_2025_Institute-of-Computer-Science-IOCS.pdf": "Indonesia; simulated data",
    "EHG_Signal_Analysis_for_Prediction_of_Term_and_Preterm_using_Variational_Mode_Decomposition_and_Artificial_Neural_Networks.pdf": "Pakistan; public EHG database",
    "Feli et al. - 2024 - Preterm birth risk stratification through longitudinal heart rate and HRV monitoring in daily life.pdf": "Finland",
    "Golob et al. - 2024 - Microbiome preterm birth DREAM challenge Crowdsourcing machine learning approaches to advance prete.pdf": "Multi-country/public cohorts",
    "Greylag-Goose-Optimization-and-Deep-LearningBased-Electrohysterogram-Signal-Analysis-for-Preterm-Birth-Risk-Prediction_2025_Tech-Science-Press.pdf": "Public EHG dataset; Saudi Arabia/Egypt/Jordan/Bahrain authors",
    "Guo et al. - 2025 - Genome-wide nucleosome footprints of plasma cfDNA predict preterm birth A case-control study.pdf": "China",
    "Hornaday et al. - 2025 - Machine learning for the prediction of spontaneous preterm birth using early second and third trimes.pdf": "Canada",
    "Huang et al. - 2024 - Predicting preterm birth using electronic medical records from multiple prenatal visits.pdf": "United States",
    "Identification of unique risk groups for preterm birth using routinely screened biomarkers and machine learning.pdf": "United States",
    "Intelligent system based on data mining techniques for prediction of preterm birth for women with cervical cerclage.pdf": "Jordan/Australia",
    "Journal of Healthcare Engineering - 2021 - Raja - A Machine Learning‐Based Prediction Model for Preterm Birth in Rural.pdf": "India",
    "Journal of Healthcare Engineering - 2022 - Sun - Machine Learning‐Based Prediction Model of Preterm Birth Using Electronic.pdf": "China",
    "Kang et al. - 2025 - An explainable machine learning model for predicting preterm birth in pregnant women with gestationa.pdf": "China",
    "Khan et al. - 2023 - Predicting preterm birth using explainable machine learning in a prospective cohort of nulliparous a.pdf": "United Arab Emirates",
    "Kloska et al. - 2025 - Predicting preterm birth using machine learning methods.pdf": "Poland",
    "LaborEase_An_Artificial_Intelligence-Based_Wearable_Electrohysterography_Device_for_Preterm_Pregnancy_Detection.pdf": "Pakistan; public EHG database",
    "Liang et al. - 2025 - Development of a spontaneous preterm birth predictive model using a panel of serum protein biomarker.pdf": "China",
    "Lin et al. - 2025 - Differential Predictability of Preterm Birth Types Strong Signals for Indicated Cases versus Limite.pdf": "United States",
    "Liu et al. - 2025 - Machine learning model‐based preterm birth prediction and clinical nomogram A big retrospective coh.pdf": "China",
    "Machine Learning Approach for Preterm Birth Prediction Based on Maternal Chronic Conditions.pdf": "India",
    "Machine_Learning_Model_to_Predict_Pre-Term_Delivery_Using_Electronic_Health_Records.pdf": "Not specified; India/United States author team",
    "Maqsood et al. - 2026 - Comparative machine learning models for early prediction of preterm birth from maternal serum biomar.pdf": "Pakistan/Saudi Arabia",
    "Mirzamoradi et al. - 2024 - A Neural Network-based Approach to Prediction of Preterm Birth using Non-invasive Tests.pdf": "Iran",
    "MobileNet-based_Prediction_of_Preterm_Births.pdf": "Pakistan; public EHG database",
    "PIIS0002937816315381.pdf": "United States",
    "PIIS0002937822011279.pdf": "United States",
    "PIIS0002937823015636.pdf": "Israel",
    "Park et al. - 2021 - Prediction of preterm birth based on machine learning using bacterial risk score in cervicovaginal f.pdf": "South Korea",
    "Prats-Boluda et al. - 2021 - Optimization of Imminent Labor Prediction Systems in Women with Threatened Preterm Labor Based on El.pdf": "Spain",
    "Precision_at_its_Core_Machine_Learning-Infused_Metabolomics_Model_for_Preterm_Birth_Prediction_in_Human.pdf": "India",
    "Prediction_Model_for_Preterm_Birth_Using_Deep_Learning.pdf": "India",
    "Prediction_of_Preterm_Pregnancies_using_Soft_Computing_techniques_Neural_Networks_and_Gradient_Descent_Optimizer.pdf": "India",
    "Preterm_Birth_Prediction_by_Classification_of_Spectral_Features_of_Electrohysterography_Signals_using_1D_Convolutional_Neural_Network_Preliminary_Results.pdf": "Turkey; public EHG database",
    "Proactive_Preterm_Labor_Prediction_Using_Ptl-Simple_RNN_Deep_Learning.pdf": "India",
    "Qian et al. - 2025 - Predicting the risk of preterm birth with machine learning and electronic health records in China.pdf": "China",
    "Realistic preterm prediction based on optimized synthetic sampling of EHG signal.pdf": "China; public EHG database",
    "Rocha et al. - 2021 - Data-driven risk stratification for preterm birth in Brazil a population-based study to develop of.pdf": "Brazil",
    "Sejer et al. - 2026 - The combined use of cervical ultrasound and deep learning improves the detection of patients at risk.pdf": "Denmark",
    "Silva et al. - 2025 - Evaluating how different balancing data techniques impact on prediction of premature birth using mac.pdf": "Brazil",
    "Synan et al. - 2023 - First Trimester Prediction of Preterm Birth in Patient Plasma with Machine-Learning-Guided Raman Spe.pdf": "United States",
    "Tai et al. - 2026 - Artificial intelligence application in the prediction of spontaneous preterm birth by cervical lengt.pdf": "Hong Kong/Taiwan",
    "Teng et al. - 2025 - Machine learning prediction of preterm birth in women under 35 using routine biomarkers in a retrosp.pdf": "China",
    "Using-an-innovative-stacked-ensemble-algorithm-for-the-accurate-prediction-of-preterm-birth_2019_Galenos-Yayincilik-infogalenoscomtr.pdf": "India",
    "Utilizing_Deep_Learning_and_Genome_Wide_Association_Studies_for_Epistatic-Driven_Preterm_Birth_Classification_in_African-American_Women.pdf": "United States",
    "Wong et al. - 2022 - Development of prognostic model for preterm birth using machine learning in a population-based cohor.pdf": "Australia",
    "Xiong et al. - 2025 - Machine learning-based prediction algorithm of spontaneous preterm birth using multi-source data.pdf": "China",
    "Yang et al. - 2025 - Prediction of spontaneous preterm birth in pregnant women using machine learning.pdf": "China",
    "Yu et al. - 2024 - Predicting risk of preterm birth in singleton pregnancies using machine learning algorithms.pdf": "China",
    "Zhang et al. - 2022 - The Prediction of Preterm Birth Using Time-Series Technology-Based Machine Learning Retrospective C.pdf": "China",
    "am3c04260_si_001.pdf": "United States",
    "children-12-01451-v2.pdf": "Greece",
    "diagnostics-16-00499.pdf": "China",
    "ijms-24-13851-v2.pdf": "Mexico",
    "jogh-13-04051.pdf": "Ethiopia",
    "s10916-017-0847-8.pdf": "Public EHG database; Algeria authors",
    "s11517-025-03293-2.pdf": "China; public EHG database",
}


DATASET_OVERRIDES = {
    "197.pdf": "Local hospital dataset from Mysuru, India; women with diabetes mellitus or gestational diabetes and maternal chronic-condition risk factors.",
    "1-s2.0-S0169260725005966-main.pdf": "Retrospective cohort of 253 pregnant women with first-trimester transvaginal ultrasound images; 28 sPTB cases.",
    "1-s2.0-S1532046419302539-main.pdf": "10 years of Vanderbilt University Medical Center EHR data from 25,689 deliveries.",
    "1-s2.0-S2352914822001927-main.pdf": "NICHD Maternal Fetal Medicine Units Network dataset; 2,390 women with no previous preterm birth and 201 sPTB cases.",
    "2709-0094-52-7-39011.pdf": "Patients with first-pregnancy cervical insufficiency and second-pregnancy outcomes at Xiamen Humanity Maternity Hospital.",
    "A-novel-sequencebased-transformer-model-architecture-for-integrating-multiomics-data-in-preterm-birth-risk-prediction_2025_Nature-Research.pdf": "Prospective FJ and LG cohorts with cfDNA/cfRNA sequencing; FJ 60 PTB and 120 term, LG 138 PTB and 364 term.",
    "ATDE-18-ATDE210243.pdf": "Term-preterm EHG database; 78 training/testing samples and 100 validation samples.",
    "A_Meta-learner_Based_Ensemble_System_of_Neural_Networks_for_Improving_the_Accuracy_of_Preterm_Birth_Prediction.pdf": "Dataset of 2,600 samples with term birth as majority class.",
    "A_Preterm_Birth_Risk_Prediction_System_for_Mobile_Health_Applications_Based_on_the_Support_Vector_Machine_Algorithm.pdf": "Pregnancy database used for SVM-based m-health decision support; sample size not clearly reported in extracted text.",
    "Abdi et al. - 2025 - Developing a prognostic model for predicting preterm birth using a machine learning algorithm.pdf": "Iranian Maternal and Neonatal Network birth records from Khaleej-e-Fars Hospital, 2020-2022; 8,853 births and 1,230 spontaneous PTB cases.",
    "Ahmad et al. - 2025 - Early prediction of very and extreme preterm births using a one-class classification framework on el.pdf": "First-trimester EHR and questionnaire risk-factor dataset from an ongoing Al Ain, UAE pregnancy study; sample size not clearly reported in extracted text.",
    "Al Ghadban et al. - 2024 - Prediction of spontaneous preterm birth using supervised machine learning on metabolomic data A cas.pdf": "Pregnancy Outcome Prediction study case-cohort; 399 participants including 98 sPTB cases, serum at 12, 20, 28, and 36 weeks.",
    "AlSaad et al. - 2022 - PredictPTB an interpretable preterm birth prediction model using attention-based recurrent neural n.pdf": "Large EHR cohort of 222,436 deliveries and 27,100 unique clinical concepts.",
    "Application of machine-learning to predict early spontaneous preterm birth among nulliparous non-Hispanic black and white women.pdf": "nuMoM2b nulliparous cohort with non-Hispanic Black and White women.",
    "Article à la page 6 Prediction of spontaneous preterm birth among twin gestations using machine learning and texture analysis of cervical ultrasound images.pdf": "98 twin gestations; 61 preterm births; mid-trimester cervical ultrasound images.",
    "Belaghi - 2024 - Prediction of preterm birth in multiparous women using logistic regression and machine learning appr.pdf": "Ontario BORN population-based cohort of 145,846 multiparous singleton births.",
    "Cervical texture analysis in mid-trimester scan to predict spontaneous preterm birth A case-control study.pdf": "381 singleton pregnancies; 178 spontaneous PTB cases and 203 term controls.",
    "Cervix_Ultrasound_Texture_Analysis_to_Differentiate_Between_Term_and_Preterm_Birth_Pregnancy_A_Machine_Learning_Approach.pdf": "Sagittal transvaginal cervical ultrasound images at 28-32 weeks; five regions of interest analyzed.",
    "Chakoory et al. - 2024 - DeepMPTB a vaginal microbiome-based deep neural network as artificial intelligence strategy for eff.pdf": "Five independent cohorts, 1,290 vaginal samples from 561 pregnant women.",
    "Chen et al. - 2024 - Development and validation of a spontaneous preterm birth risk prediction algorithm based on materna.pdf": "Retrospective clinical/laboratory data from 3,082 pregnant women plus external validation data.",
    "Cheng et al. - 2022 - Novel Multichannel Entropy Features and Machine Learning for Early Assessment of Pregnancy Progressi.pdf": "Annotated database of 74 EHG recordings from women with preterm contractions.",
    "Cohen et al. - 2024 - 736 Identifying women at high risk for preterm birth based on clinical data using machine learning.pdf": "Clinical data abstract; sample details limited in extracted text.",
    "Computational and Mathematical Methods in Medicine - 2017 - Chen - Feature Extraction and Classification of EHG between.pdf": "Pregnancy and labor EHG recordings used for Hilbert-Huang feature extraction and classification; sample size not clearly reported.",
    "Costanzo et al. - 2025 - Prediction of preterm birth from cervical length measurements in twin pregnancies using machine lear.pdf": "Twin-pregnancy cervical length datasets with multiple aggregation strategies.",
    "Data-driven risk stratification for preterm birth in Brazil a population-based study to develop of a machine learning risk assessment approach.pdf": "Brazilian national live-birth and contextual datasets used for population risk stratification.",
    "Ding et al. - 2024 - Prediction of preterm birth using machine learning a comprehensive analysis based on large-scale pr.pdf": "Large-scale preschool children survey data from Shenzhen, China.",
    "Dynamic-Model-for-Early-Detection-of-Preterm-Labor_2025_Institute-of-Computer-Science-IOCS.pdf": "Dummy/simulated multivariate time-series data for 500 virtual pregnancies; no real patient data.",
    "EHG_Signal_Analysis_for_Prediction_of_Term_and_Preterm_using_Variational_Mode_Decomposition_and_Artificial_Neural_Networks.pdf": "Public term/preterm EHG signal dataset processed with variational mode decomposition; sample size not clearly reported.",
    "Feli et al. - 2024 - Preterm birth risk stratification through longitudinal heart rate and HRV monitoring in daily life.pdf": "Longitudinal smartwatch PPG from 58 pregnant women, including 7 preterm cases.",
    "Golob et al. - 2024 - Microbiome preterm birth DREAM challenge Crowdsourcing machine learning approaches to advance prete.pdf": "Nine vaginal microbiome studies; 3,578 samples from 1,268 pregnant individuals plus two unpublished validation datasets.",
    "Greylag-Goose-Optimization-and-Deep-LearningBased-Electrohysterogram-Signal-Analysis-for-Preterm-Birth-Risk-Prediction_2025_Tech-Science-Press.pdf": "58 samples of 1,000-second EHG recordings.",
    "Guo et al. - 2025 - Genome-wide nucleosome footprints of plasma cfDNA predict preterm birth A case-control study.pdf": "Whole-genome cfDNA sequencing from 20 preterm and 20 full-term pregnancies.",
    "Huang et al. - 2024 - Predicting preterm birth using electronic medical records from multiple prenatal visits.pdf": "nuMoM2b data from 8,830 nulliparous women across three prenatal visits.",
    "Identification of unique risk groups for preterm birth using routinely screened biomarkers and machine learning.pdf": "AJOG poster abstract using routinely screened biomarker groups; sample size not clearly reported in extracted text.",
    "Intelligent system based on data mining techniques for prediction of preterm birth for women with cervical cerclage.pdf": "274 pregnancies managed with cervical cerclage, including 29 multiple pregnancies.",
    "Journal of Healthcare Engineering - 2021 - Raja - A Machine Learning‐Based Prediction Model for Preterm Birth in Rural.pdf": "Obstetrical data collected from the Community Health Centre in Kamdara, Jharkhand, India.",
    "Khan et al. - 2023 - Predicting preterm birth using explainable machine learning in a prospective cohort of nulliparous a.pdf": "Prospective UAE Mutaba'ah cohort of 3,509 pregnant women.",
    "Kloska et al. - 2025 - Predicting preterm birth using machine learning methods.pdf": "Clinical and blood-test data from 50 maternity ward patients.",
    "LaborEase_An_Artificial_Intelligence-Based_Wearable_Electrohysterography_Device_for_Preterm_Pregnancy_Detection.pdf": "LaborEase recordings combined with the open TPEHGDB dataset.",
    "Liu et al. - 2025 - Machine learning model‐based preterm birth prediction and clinical nomogram A big retrospective coh.pdf": "2,688,568 mother-infant pairs from a 2018 cohort.",
    "Machine Learning Approach for Preterm Birth Prediction Based on Maternal Chronic Conditions.pdf": "Local hospital dataset from Mysuru, India; women with diabetes mellitus or gestational diabetes and maternal chronic-condition risk factors.",
    "Machine_Learning_Model_to_Predict_Pre-Term_Delivery_Using_Electronic_Health_Records.pdf": "Retrospective EHR cohort of over 5,400 pregnancies.",
    "Maqsood et al. - 2026 - Comparative machine learning models for early prediction of preterm birth from maternal serum biomar.pdf": "Maternal serum inflammatory and lipid biomarker dataset; sample size not clear in extracted text.",
    "Mirzamoradi et al. - 2024 - A Neural Network-based Approach to Prediction of Preterm Birth using Non-invasive Tests.pdf": "Historical cohort using 13 questionnaire/clinical risk factors; non-invasive inputs.",
    "MobileNet-based_Prediction_of_Preterm_Births.pdf": "EHG records processed as deep-learning inputs; dataset source not clearly specified in extracted text.",
    "PIIS0002937816315381.pdf": "Conference abstract using routinely screened biomarkers; sample details limited in extracted text.",
    "PIIS0002937822011279.pdf": "Consortium on Safe Labor data; 228,438 pregnancies, 10,000 held out for testing.",
    "PIIS0002937823015636.pdf": "Clinical data from all live deliveries in a tertiary hospital, 2013-2023; 63,937 deliveries with 3,772 sPTB cases.",
    "Park et al. - 2021 - Prediction of preterm birth based on machine learning using bacterial risk score in cervicovaginal f.pdf": "Cervicovaginal fluid microbiota/bacterial risk score data from pregnant women.",
    "Prats-Boluda et al. - 2021 - Optimization of Imminent Labor Prediction Systems in Women with Threatened Preterm Labor Based on El.pdf": "EHG recordings from women with threatened preterm labor for imminent delivery prediction.",
    "Prediction_of_Preterm_Pregnancies_using_Soft_Computing_techniques_Neural_Networks_and_Gradient_Descent_Optimizer.pdf": "Delivery records using maternal height, age, gravida, para, LMP, blood group, delivery, and baby survival fields; sample size not clearly reported.",
    "Preterm_Birth_Prediction_by_Classification_of_Spectral_Features_of_Electrohysterography_Signals_using_1D_Convolutional_Neural_Network_Preliminary_Results.pdf": "EHG database records represented by spectral features for 1D CNN classification; sample size not clearly reported.",
    "Proactive_Preterm_Labor_Prediction_Using_Ptl-Simple_RNN_Deep_Learning.pdf": "Clinical time-series dataset for Simple RNN PTL prediction not clearly specified in extracted text.",
    "Synan et al. - 2023 - First Trimester Prediction of Preterm Birth in Patient Plasma with Machine-Learning-Guided Raman Spe.pdf": "First-trimester plasma from 37 patients: 20 PTB and 17 term controls.",
    "Tai et al. - 2026 - Artificial intelligence application in the prediction of spontaneous preterm birth by cervical lengt.pdf": "1,664 first-trimester transvaginal cervical ultrasound images from a prospective Hong Kong study.",
    "Using-an-innovative-stacked-ensemble-algorithm-for-the-accurate-prediction-of-preterm-birth_2019_Galenos-Yayincilik-infogalenoscomtr.pdf": "Historical data of expectant mothers; sample size not clearly reported in extracted text.",
    "Utilizing_Deep_Learning_and_Genome_Wide_Association_Studies_for_Epistatic-Driven_Preterm_Birth_Classification_in_African-American_Women.pdf": "GWAS/genotype data for African-American women; sample size not clearly reported in extracted text.",
    "Yu et al. - 2024 - Predicting risk of preterm birth in singleton pregnancies using machine learning algorithms.pdf": "Prospective population-based Wenzhou cohort of 22,603 singleton pregnancies.",
    "am3c04260_si_001.pdf": "Supplementary figures, tables, and model details for the linked 37-patient Raman spectroscopy/metabolomics study.",
    "jogh-13-04051.pdf": "Amhara region Ethiopia pregnancy and birth cohort; 2,493 pregnancies included.",
    "children-12-01451-v2.pdf": "Single tertiary institution cohort, 2012-2025; 9,805 singleton pregnancies.",
    "ijms-24-13851-v2.pdf": "Cervical-vaginal mucus cytokine and clinical data from pregnant women at 18-23.6 weeks.",
    "s10916-017-0847-8.pdf": "Thirty-minute term and preterm EHG signals collected between 27 and 32 gestational weeks; three bipolar channels per recording.",
    "s11517-025-03293-2.pdf": "TPEHG database; 300 EHG recordings.",
}


RESULT_OVERRIDES = {
    "A_Preterm_Birth_Risk_Prediction_System_for_Mobile_Health_Applications_Based_on_the_Support_Vector_Machine_Algorithm.pdf": "SVM-based approach achieved accuracy 0.821, true positive rate 0.839, false positive rate 0.268, and ROC area 0.785.",
    "Cervix_Ultrasound_Texture_Analysis_to_Differentiate_Between_Term_and_Preterm_Birth_Pregnancy_A_Machine_Learning_Approach.pdf": "At a fixed 10% false positive rate, the multilayer perceptron model achieved 67% sensitivity for distinguishing term and preterm delivery.",
    "Computational and Mathematical Methods in Medicine - 2017 - Chen - Feature Extraction and Classification of EHG between.pdf": "The proposed HHT and extreme learning machine approach reached accuracy 88.00%, sensitivity 91.30%, and specificity 85.19%.",
    "Cohen et al. - 2024 - 736 Identifying women at high risk for preterm birth based on clinical data using machine learning.pdf": "In 63,937 deliveries, 3,772 (5.9%) had sPTB. The first-trimester model identified 2% of the population with 50% sPTB probability, representing 25% of sPTB cases; among suspected sPTB admissions, 17% were flagged with near-certain delivery within 7 days (recall 0.5).",
    "PIIS0002937823015636.pdf": "In 63,937 deliveries, 3,772 (5.9%) had sPTB. The first-trimester model identified 2% of the population with 50% sPTB probability, representing 25% of sPTB cases; among suspected sPTB admissions, 17% were flagged with near-certain delivery within 7 days (recall 0.5).",
    "Data-driven risk stratification for preterm birth in Brazil a population-based study to develop of a machine learning risk assessment approach.pdf": "XGBoost predicted week of delivery with average RMSE 2.094 weeks. Key predictors included prior C-section, number of prenatal consultations, maternal age, ultrasound availability, and oral care consultation registration.",
    "EHG_Signal_Analysis_for_Prediction_of_Term_and_Preterm_using_Variational_Mode_Decomposition_and_Artificial_Neural_Networks.pdf": "Variational mode decomposition features with an artificial neural network achieved 98.8% average accuracy using 10-fold cross-validation.",
    "Journal of Healthcare Engineering - 2021 - Raja - A Machine Learning‐Based Prediction Model for Preterm Birth in Rural.pdf": "The SVM classifier achieved 90.9% accuracy, outperforming the other classifiers evaluated in the study.",
    "Rocha et al. - 2021 - Data-driven risk stratification for preterm birth in Brazil a population-based study to develop of.pdf": "XGBoost predicted week of delivery with average RMSE 2.094 weeks. Key predictors included prior C-section, number of prenatal consultations, maternal age, ultrasound availability, and oral care consultation registration.",
    "Prediction_Model_for_Preterm_Birth_Using_Deep_Learning.pdf": "The paper proposes a deep-learning PTB prediction model, but empirical validation metrics were not clearly reported in the extracted text.",
    "Proactive_Preterm_Labor_Prediction_Using_Ptl-Simple_RNN_Deep_Learning.pdf": "The Simple RNN framework is presented as an adaptive PTL risk model; detailed validation metrics were not clearly reported in the extracted text.",
    "Sejer et al. - 2026 - The combined use of cervical ultrasound and deep learning improves the detection of patients at risk.pdf": "Final dataset included 4,224 pregnancies and 7,862 cervical ultrasound images. AI outperformed cervical length for sPTB <37 weeks: sensitivity 0.51 vs 0.41 at specificity 0.85, and AUC 0.75 vs 0.67.",
    "Using-an-innovative-stacked-ensemble-algorithm-for-the-accurate-prediction-of-preterm-birth_2019_Galenos-Yayincilik-infogalenoscomtr.pdf": "Innovative stacked ensemble learning predicted PTB with more than 96% accuracy in the study experiments.",
}


POPULATION_OVERRIDES = {
    "1-s2.0-S0169260725005966-main.pdf": "Pregnant women screened at 11+0 to 13+6 weeks.",
    "1-s2.0-S1532046419302539-main.pdf": "Pregnant patients/deliveries in an academic medical center EHR.",
    "1-s2.0-S2352914822001927-main.pdf": "Women with no previous preterm birth in the MFMU cohort.",
    "2709-0094-52-7-39011.pdf": "Women with prior cervical insufficiency entering a second pregnancy.",
    "A-novel-sequencebased-transformer-model-architecture-for-integrating-multiomics-data-in-preterm-birth-risk-prediction_2025_Nature-Research.pdf": "Pregnant women with cfDNA/cfRNA samples followed to PTB or term birth.",
    "Al Ghadban et al. - 2024 - Prediction of spontaneous preterm birth using supervised machine learning on metabolomic data A cas.pdf": "Pregnancy Outcome Prediction study participants with sequential serum samples.",
    "AlSaad et al. - 2022 - PredictPTB an interpretable preterm birth prediction model using attention-based recurrent neural n.pdf": "Pregnant patients represented in longitudinal EHR visits.",
    "Application of machine-learning to predict early spontaneous preterm birth among nulliparous non-Hispanic black and white women.pdf": "Nulliparous non-Hispanic Black and White women.",
    "Article à la page 6 Prediction of spontaneous preterm birth among twin gestations using machine learning and texture analysis of cervical ultrasound images.pdf": "Women with twin gestations.",
    "Belaghi - 2024 - Prediction of preterm birth in multiparous women using logistic regression and machine learning appr.pdf": "Multiparous women with singleton births.",
    "Cervical texture analysis in mid-trimester scan to predict spontaneous preterm birth A case-control study.pdf": "Singleton pregnancies with spontaneous vaginal delivery.",
    "Chakoory et al. - 2024 - DeepMPTB a vaginal microbiome-based deep neural network as artificial intelligence strategy for eff.pdf": "Pregnant women with vaginal microbiome samples.",
    "Chen et al. - 2024 - Development and validation of a spontaneous preterm birth risk prediction algorithm based on materna.pdf": "Pregnant women with clinical and laboratory assessments.",
    "Cheng et al. - 2022 - Novel Multichannel Entropy Features and Machine Learning for Early Assessment of Pregnancy Progressi.pdf": "Women with preterm contractions and EHG recordings.",
    "Costanzo et al. - 2025 - Prediction of preterm birth from cervical length measurements in twin pregnancies using machine lear.pdf": "Women with twin pregnancies and serial cervical length measurements.",
    "Ding et al. - 2024 - Prediction of preterm birth using machine learning a comprehensive analysis based on large-scale pr.pdf": "Children/maternal records from Shenzhen survey data.",
    "Feli et al. - 2024 - Preterm birth risk stratification through longitudinal heart rate and HRV monitoring in daily life.pdf": "Pregnant women monitored in daily life with smartwatches.",
    "Golob et al. - 2024 - Microbiome preterm birth DREAM challenge Crowdsourcing machine learning approaches to advance prete.pdf": "Pregnant individuals from multiple vaginal microbiome cohorts.",
    "Guo et al. - 2025 - Genome-wide nucleosome footprints of plasma cfDNA predict preterm birth A case-control study.pdf": "Pregnant women in PTB and full-term case-control groups.",
    "Huang et al. - 2024 - Predicting preterm birth using electronic medical records from multiple prenatal visits.pdf": "Nulliparous women across multiple prenatal visits.",
    "Intelligent system based on data mining techniques for prediction of preterm birth for women with cervical cerclage.pdf": "High-risk pregnant women undergoing cervical cerclage.",
    "Khan et al. - 2023 - Predicting preterm birth using explainable machine learning in a prospective cohort of nulliparous a.pdf": "Nulliparous and multiparous pregnant women.",
    "Kloska et al. - 2025 - Predicting preterm birth using machine learning methods.pdf": "Maternity ward patients with term or preterm delivery.",
    "LaborEase_An_Artificial_Intelligence-Based_Wearable_Electrohysterography_Device_for_Preterm_Pregnancy_Detection.pdf": "Pregnant women with wearable EHG recordings and public EHG records.",
    "Liu et al. - 2025 - Machine learning model‐based preterm birth prediction and clinical nomogram A big retrospective coh.pdf": "Mother-infant pairs in a large retrospective cohort.",
    "Maqsood et al. - 2026 - Comparative machine learning models for early prediction of preterm birth from maternal serum biomar.pdf": "Pregnant women with maternal serum inflammatory and lipid markers.",
    "Mirzamoradi et al. - 2024 - A Neural Network-based Approach to Prediction of Preterm Birth using Non-invasive Tests.pdf": "Pregnant women characterized by non-invasive clinical/questionnaire factors.",
    "Park et al. - 2021 - Prediction of preterm birth based on machine learning using bacterial risk score in cervicovaginal f.pdf": "Pregnant women with cervicovaginal fluid bacterial profiles.",
    "Prats-Boluda et al. - 2021 - Optimization of Imminent Labor Prediction Systems in Women with Threatened Preterm Labor Based on El.pdf": "Women with threatened preterm labor.",
    "Tai et al. - 2026 - Artificial intelligence application in the prediction of spontaneous preterm birth by cervical lengt.pdf": "Women with viable singleton pregnancies undergoing Down syndrome screening.",
    "Yu et al. - 2024 - Predicting risk of preterm birth in singleton pregnancies using machine learning algorithms.pdf": "Singleton pregnancies in a prospective population-based cohort.",
    "jogh-13-04051.pdf": "Pregnant women in a rural Ethiopian birth cohort.",
    "children-12-01451-v2.pdf": "Singleton pregnancies at mid-gestation.",
    "ijms-24-13851-v2.pdf": "Pregnant women at 18-23.6 weeks with high or low PTB risk by cervical length.",
}


DATA_MODALITY_OVERRIDES = {
    "1-s2.0-S1532046419302539-main.pdf": "Electronic health records/clinical records",
    "A-novel-sequencebased-transformer-model-architecture-for-integrating-multiomics-data-in-preterm-birth-risk-prediction_2025_Nature-Research.pdf": "Multi-omics cfDNA/cfRNA sequencing",
    "Feli et al. - 2024 - Preterm birth risk stratification through longitudinal heart rate and HRV monitoring in daily life.pdf": "Wearable PPG heart rate and HRV",
    "Golob et al. - 2024 - Microbiome preterm birth DREAM challenge Crowdsourcing machine learning approaches to advance prete.pdf": "Vaginal microbiome sequencing",
    "Guo et al. - 2025 - Genome-wide nucleosome footprints of plasma cfDNA predict preterm birth A case-control study.pdf": "Plasma cfDNA whole-genome sequencing",
    "Hornaday et al. - 2025 - Machine learning for the prediction of spontaneous preterm birth using early second and third trimes.pdf": "Maternal blood gene expression",
    "Cohen et al. - 2024 - 736 Identifying women at high risk for preterm birth based on clinical data using machine learning.pdf": "Clinical records/risk factors",
    "PIIS0002937823015636.pdf": "Clinical records/risk factors",
    "Huang et al. - 2024 - Predicting preterm birth using electronic medical records from multiple prenatal visits.pdf": "Electronic health records/clinical records",
    "Intelligent system based on data mining techniques for prediction of preterm birth for women with cervical cerclage.pdf": "Clinical cerclage and obstetric records",
    "Journal of Healthcare Engineering - 2022 - Sun - Machine Learning‐Based Prediction Model of Preterm Birth Using Electronic.pdf": "Electronic health records/clinical records",
    "Lin et al. - 2025 - Differential Predictability of Preterm Birth Types Strong Signals for Indicated Cases versus Limite.pdf": "Clinical and prenatal visit variables",
    "Mirzamoradi et al. - 2024 - A Neural Network-based Approach to Prediction of Preterm Birth using Non-invasive Tests.pdf": "Non-invasive clinical/questionnaire variables",
    "PIIS0002937822011279.pdf": "Clinical obstetric records",
    "Precision_at_its_Core_Machine_Learning-Infused_Metabolomics_Model_for_Preterm_Birth_Prediction_in_Human.pdf": "Metabolomics/clinical biomarker data",
    "Prediction_Model_for_Preterm_Birth_Using_Deep_Learning.pdf": "Proposed multimodal EHR, EHG, and ultrasound inputs",
    "Wong et al. - 2022 - Development of prognostic model for preterm birth using machine learning in a population-based cohor.pdf": "Population birth registry/administrative records",
    "Yu et al. - 2024 - Predicting risk of preterm birth in singleton pregnancies using machine learning algorithms.pdf": "Antenatal surveillance and clinical records",
    "Zhang et al. - 2022 - The Prediction of Preterm Birth Using Time-Series Technology-Based Machine Learning Retrospective C.pdf": "Time-series obstetric examination records",
    "Synan et al. - 2023 - First Trimester Prediction of Preterm Birth in Patient Plasma with Machine-Learning-Guided Raman Spe.pdf": "Plasma Raman spectroscopy and metabolomics",
    "am3c04260_si_001.pdf": "Supplementary Raman/metabolomics data",
    "ijms-24-13851-v2.pdf": "Cervical-vaginal mucus cytokines and cervical length",
    "jogh-13-04051.pdf": "Clinical, sociodemographic, environmental, and pregnancy cohort data",
}


PUBLICATION_TYPE_OVERRIDES = {
    "Article à la page 6 Prediction of spontaneous preterm birth among twin gestations using machine learning and texture analysis of cervical ultrasound images.pdf": "Journal article",
    "Cohen et al. - 2024 - 736 Identifying women at high risk for preterm birth based on clinical data using machine learning.pdf": "Conference abstract/poster",
    "Identification of unique risk groups for preterm birth using routinely screened biomarkers and machine learning.pdf": "Conference abstract/poster",
    "PIIS0002937816315381.pdf": "Conference abstract/poster",
    "PIIS0002937822011279.pdf": "Conference abstract/poster",
    "PIIS0002937823015636.pdf": "Conference abstract/poster",
    "Lin et al. - 2025 - Differential Predictability of Preterm Birth Types Strong Signals for Indicated Cases versus Limite.pdf": "Preprint",
    "Ding et al. - 2024 - Prediction of preterm birth using machine learning a comprehensive analysis based on large-scale pr.pdf": "Journal article",
    "Utilizing_Deep_Learning_and_Genome_Wide_Association_Studies_for_Epistatic-Driven_Preterm_Birth_Classification_in_African-American_Women.pdf": "Journal article",
    "am3c04260_si_001.pdf": "Supplementary information",
    "jogh-13-04051.pdf": "Journal article",
}


def norm(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def filename_title(name):
    stem = Path(name).stem
    match = re.search(r" - (20\d{2}) - (.+)$", stem)
    if match:
        return norm(match.group(2).replace("_", " "))
    return norm(re.sub(r"[_-]+", " ", stem))


def title_for(article):
    name = article["file_name"]
    if name in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[name]
    meta = norm(article.get("metadata_title", ""))
    candidate = norm(article.get("title_candidate", ""))
    bad = ["untitled", "ijobas", "open ", "bmc pregnancy", "bmc medical", "jmIR medical", "clin. exp.", "ajog.org"]
    if meta and len(meta) > 12 and not any(b.lower() in meta.lower() for b in bad):
        return meta
    if candidate and len(candidate) > 12 and not any(b.lower() in candidate.lower() for b in bad):
        return candidate
    return filename_title(name)


def doi_for(article):
    name = article["file_name"]
    if name in DOI_OVERRIDES:
        return DOI_OVERRIDES[name]
    doi = norm(article.get("doi", ""))
    doi = doi.replace(" ", "")
    if doi in {"10.1093/neuros/"} or doi.endswith("/"):
        return ""
    return doi


def year_for(article):
    name = article["file_name"]
    if name in YEAR_OVERRIDES:
        return YEAR_OVERRIDES[name]
    title = title_for(article)
    blob = " ".join([name, article.get("first_page", ""), title])
    # Prefer explicit publication/volume years in the first page.
    years = re.findall(r"\b20(?:1[5-9]|2[0-6])\b", blob[:5000])
    if years:
        # The first year is usually the journal/conference year; filename dates also occur early.
        return years[0]
    return "not reported"


def publication_type(article):
    name = article["file_name"]
    if name in PUBLICATION_TYPE_OVERRIDES:
        return PUBLICATION_TYPE_OVERRIDES[name]
    text = (article["file_name"] + " " + article.get("first_page", "")).lower()
    doi = doi_for(article).lower()
    if "supplement" in text or name.endswith("_si_001.pdf"):
        return "Supplementary information"
    if "10.1101" in doi or "preprint" in text or "medrxiv" in text or "biorxiv" in text:
        return "Preprint"
    if "conference" in text or "10.1109" in doi or "ieee" in text:
        return "Conference paper"
    if article.get("pages") and article["pages"] <= 2:
        return "Conference abstract/poster"
    return "Journal article"


def data_modality(article):
    name = article["file_name"]
    if name in DATA_MODALITY_OVERRIDES:
        return DATA_MODALITY_OVERRIDES[name]
    blob = norm(" ".join([title_for(article), article.get("abstract", ""), article.get("first_page", ""), article.get("methods", "")])).lower()
    if "electrohyster" in blob or re.search(r"\behg\b", blob):
        return "Electrohysterogram (EHG) signals"
    if "ultrasound" in blob or "cervical length" in blob or "cervix" in blob or "radiomic" in blob or "texture" in blob:
        return "Cervical ultrasound/image-derived features"
    if "microbiome" in blob or "metagenomic" in blob or "bacterial risk" in blob:
        return "Vaginal/cervicovaginal microbiome"
    if "metabol" in blob or "serum" in blob or "protein biomarker" in blob or "cytokine" in blob:
        return "Serum/plasma biomarkers or metabolomics"
    if "cfdna" in blob or "cfrna" in blob or "gene expression" in blob or "genome" in blob or "gwas" in blob:
        return "Genomic/transcriptomic/omics data"
    if "electronic health" in blob or re.search(r"\behr\b", blob) or "medical record" in blob:
        return "Electronic health records/clinical records"
    if "heart rate" in blob or "hrv" in blob or "wearable" in blob:
        return "Wearable physiologic monitoring"
    return "Clinical, obstetric, demographic, or laboratory variables"


ALGO_PATTERNS = [
    ("GeneLLM/transformer", r"\bgene ?llm\b|transformer|large language model"),
    ("ResUNet/UNet", r"resunet|u-net|unet"),
    ("MobileNet", r"mobilenet"),
    ("CNN", r"convolutional|1d convolution|cnn"),
    ("RNN", r"recurrent neural|simple rnn|\brnn\b"),
    ("LSTM", r"\blstm\b|long short-term"),
    ("attention", r"attention"),
    ("deep neural network", r"deep neural|dnn"),
    ("neural network/ANN", r"neural network|ann|multilayer perceptron|mlp"),
    ("XGBoost", r"xgboost|extreme gradient"),
    ("LightGBM", r"lightgbm"),
    ("CatBoost", r"catboost|categorical boosting"),
    ("random forest", r"random forest"),
    ("decision tree", r"decision tree"),
    ("gradient boosting", r"gradient boosting|adaboost"),
    ("SVM", r"support vector|\bsvm\b"),
    ("logistic regression", r"logistic regression"),
    ("KNN", r"k-nearest|\bknn\b|k-nn"),
    ("Naive Bayes", r"na[iï]ve bayes"),
    ("Gaussian process", r"gaussian process"),
    ("extreme learning machine", r"extreme learning machine|\belm\b"),
    ("Cox/AFT models", r"\bcox\b|accelerated failure time"),
    ("LASSO/elastic net", r"lasso|elastic net"),
    ("SHAP", r"\bshap\b|shapley"),
    ("LIME", r"\blime\b"),
    ("SMOTE/data balancing", r"smote|oversampling|data balancing|synthetic sampling"),
    ("radiomics/texture analysis", r"radiomic|texture analysis"),
    ("MEMD/EMD/HHT feature extraction", r"memd|empirical mode|hilbert|hht|variational mode|vmd"),
    ("Bayesian updating", r"bayesian"),
    ("autoencoder", r"autoencoder"),
    ("stacked ensemble/meta-learner", r"stacked ensemble|meta[- ]learner|ensemble"),
]


def ai_tools(article):
    blob = norm(" ".join([
        title_for(article),
        article.get("abstract", ""),
        article.get("methods", ""),
        article.get("results", ""),
        " ".join(article.get("evidence_sentences", [])),
    ])).lower()
    found = []
    for label, pattern in ALGO_PATTERNS:
        if re.search(pattern, blob):
            found.append(label)
    if not found and "machine learning" in blob:
        found.append("machine learning models")
    return "; ".join(found[:10]) or "not clearly specified"


def result_sentence(article):
    if article["file_name"] in RESULT_OVERRIDES:
        return RESULT_OVERRIDES[article["file_name"]]
    text = norm(" ".join([
        article.get("abstract", ""),
        article.get("results", ""),
        article.get("conclusion", ""),
        " ".join(article.get("evidence_sentences", [])[:10]),
    ]))
    sentences = re.split(r"(?<=[.!?])\s+", text)
    hits = []
    for s in sentences:
        low = s.lower()
        if any(k in low for k in ["auc", "auroc", "accuracy", "sensitivity", "specificity", "f1", "roc", "performed best", "outperform", "achieved"]):
            s = norm(s)
            if len(s) > 35 and s not in hits:
                hits.append(s)
    if hits:
        return " ".join(hits[:2])[:900]
    if article.get("results"):
        return norm(article["results"])[:700]
    if article.get("abstract"):
        return norm(article["abstract"])[:700]
    return "Not clearly reported in extracted text."


def context_for(article):
    modality = data_modality(article)
    title = title_for(article).lower()
    if "imminent labor" in title or "preterm labor" in title:
        return f"Maternal-fetal monitoring and early warning for preterm labor using {modality}."
    if "spontaneous" in title:
        return f"Risk prediction for spontaneous preterm birth using {modality}."
    if "twin" in title:
        return f"Preterm birth risk prediction in twin gestations using {modality}."
    if "extreme" in title or "very" in title:
        return f"Prediction of very or extreme preterm birth using {modality}."
    return f"Preterm birth risk prediction using {modality}."


def problem_for(article):
    title = title_for(article).lower()
    modality = data_modality(article)
    if "imminent labor" in title or "preterm labor" in title:
        return "Existing clinical methods have limited positive predictive value for determining which symptomatic women will deliver soon."
    if "first trimester" in title:
        return "Clinical screening often identifies risk too late; earlier first-trimester stratification is needed."
    if "twin" in title:
        return "Twin pregnancies have high PTB risk and cervical length alone has limited predictive accuracy."
    if "microbiome" in modality.lower():
        return "Microbial signatures may improve prediction, but models must generalize across heterogeneous cohorts."
    if "ehr" in modality.lower() or "clinical" in modality.lower():
        return "Traditional risk-factor models miss complex interactions and have modest discrimination."
    return "Current PTB screening has limited sensitivity, specificity, timing, or interpretability for clinical decision support."


def contribution_for(article):
    title = title_for(article)
    tools = ai_tools(article)
    modality = data_modality(article)
    if publication_type(article) == "Supplementary information":
        return "Provides supplementary methods/tables for the linked Raman spectroscopy and metabolomics PTB prediction study."
    return f"Developed or evaluated {tools} to predict PTB-related outcomes from {modality}."


def limitations_for(article):
    text = norm(article.get("limitations", ""))
    if text and len(text) > 50:
        return text[:700]
    ptype = publication_type(article)
    modality = data_modality(article).lower()
    dataset = DATASET_OVERRIDES.get(article["file_name"], "").lower()
    if ptype == "Conference abstract/poster":
        return "Conference abstract/poster format limits methodological detail and external validation reporting."
    if ptype == "Supplementary information":
        return "Supplementary material only; interpret alongside the main article."
    if "simulated" in dataset or "dummy" in dataset:
        return "Uses simulated/dummy data only; real-world clinical validation is still needed."
    if "public ehg" in COUNTRY_OVERRIDES.get(article["file_name"], "").lower() or "ehg" in modality:
        return "Often based on small or public EHG datasets; external clinical validation and class-imbalance handling remain important."
    if any(k in dataset for k in ["50 ", "58 ", "37 ", "40 ", "98 ", "74 "]):
        return "Small sample size limits precision and generalizability; independent validation is needed."
    if "retrospective" in (article.get("abstract", "") + article.get("first_page", "")).lower():
        return "Retrospective design; external and prospective validation are needed before clinical deployment."
    return "External validation, calibration, and clinical implementation impact were limited or not clearly reported in the extracted text."


def dataset_for(article):
    if article["file_name"] in DATASET_OVERRIDES:
        return DATASET_OVERRIDES[article["file_name"]]
    text = norm(" ".join([article.get("abstract", ""), article.get("methods", ""), " ".join(article.get("evidence_sentences", [])[:6])]))
    patterns = [
        r"(?:total of|included|cohort of|data from|evaluated using|dataset consists of|study analyzed|leveraging)\s+[^.]{0,180}",
        r"\b\d{2,3}(?:,\d{3})?\s+(?:pregnancies|pregnant women|deliveries|samples|records|participants|patients|women|births)[^.]{0,140}",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            return norm(m.group(0))[:500]
    return "Not clearly reported in extracted text."


def population_for(article):
    if article["file_name"] in POPULATION_OVERRIDES:
        return POPULATION_OVERRIDES[article["file_name"]]
    blob = (title_for(article) + " " + article.get("abstract", "") + " " + article.get("first_page", "")).lower()
    if "twin" in blob:
        return "Women with twin pregnancies."
    if "nulliparous" in blob:
        return "Nulliparous pregnant women."
    if "multiparous" in blob:
        return "Multiparous pregnant women."
    if "cervical cerclage" in blob:
        return "Pregnant women with cervical cerclage."
    if "gestational diabetes" in blob:
        return "Pregnant women with gestational diabetes or hypertensive disorders."
    if "african-american" in blob or "african american" in blob:
        return "African-American women."
    if "pregnant" in blob:
        return "Pregnant women."
    return "Pregnancies/deliveries represented in the study dataset."


def clean_doi_spacing(doi):
    return doi.replace("10.1016/j.lana.2021.10053", "10.1016/j.lana.2021.100053")


def build_rows():
    data = json.loads(Path("outputs/scoping_review_extraction/digests.json").read_text(encoding="utf-8"))
    rows = []
    for article in data["articles"]:
        if article["file_name"] in EXCLUDE_DUPLICATE_OR_SUPPLEMENT_FILES:
            continue
        rows.append({
            "title": title_for(article),
            "country": COUNTRY_OVERRIDES.get(article["file_name"], "Not clearly reported in extracted text."),
            "year": year_for(article),
            "doi": clean_doi_spacing(doi_for(article)),
            "context": context_for(article),
            "problem": problem_for(article),
            "ai_tools": ai_tools(article),
            "contribution": contribution_for(article),
            "results": result_sentence(article),
            "dataset": dataset_for(article),
            "data_modality": data_modality(article),
            "population": population_for(article),
            "limitations": limitations_for(article),
            "publication_type": publication_type(article),
        })
    return rows


def main():
    out = Path("outputs/scoping_review_articles_extraction.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
