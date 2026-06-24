import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, classification_report, accuracy_score

# Ruta del dataset
SCRATCH_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(SCRATCH_DIR, "retrovision_ml_dataset.csv")

def train_retrovision_models():
    print("=========================================================")
    print("RetroVision - Tubería de Entrenamiento Multicámara para ML")
    print("=========================================================")
    
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"No se encontró el dataset en '{DATASET_PATH}'. Ejecuta primero el generador.")
        
    # 1. Cargar el dataset
    print("[*] Cargando dataset de analíticas...")
    df = pd.read_csv(DATASET_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Ordenar estrictamente cronológico dentro de cada cámara
    df = df.sort_values(by=['camera_id', 'timestamp']).reset_index(drop=True)
    print(f"    - Tamaño cargado: {df.shape[0]} filas, {df.shape[1]} columnas")
    print(f"    - Cámaras identificadas: {df['camera_id'].unique().tolist()}")
    
    # 2. Ingeniería de Características por Cámara (groupby para evitar leaks de cruce de cámaras)
    print("[*] Extrayendo características temporales y rezagos por cámara...")
    
    # Rezagos (Lags) de afluencia agrupados por cámara
    df['inflow_lag_1h'] = df.groupby('camera_id')['visitor_inflow'].shift(1)
    df['inflow_lag_2h'] = df.groupby('camera_id')['visitor_inflow'].shift(2)
    df['inflow_lag_24h'] = df.groupby('camera_id')['visitor_inflow'].shift(24)
    
    # Promedio móvil de afluencia (últimas 3 horas)
    df['inflow_rolling_mean_3h'] = df.groupby('camera_id')['visitor_inflow'].shift(1).rolling(window=3).mean()
    
    # Rezagos de tiempo de espera agrupados por cámara
    df['wait_lag_1h'] = df.groupby('camera_id')['avg_wait_time_seconds'].shift(1)
    df['wait_lag_2h'] = df.groupby('camera_id')['avg_wait_time_seconds'].shift(2)
    df['wait_lag_24h'] = df.groupby('camera_id')['avg_wait_time_seconds'].shift(24)
    
    # Rezago de personas en cola
    df['queue_lag_1h'] = df.groupby('camera_id')['personas_en_cola'].shift(1)
    
    # 3. Definir Variables Objetivo (Targets) a predecir (t+1) por cámara
    df['target_inflow_next_hour'] = df.groupby('camera_id')['visitor_inflow'].shift(-1)
    df['target_wait_next_hour'] = df.groupby('camera_id')['avg_wait_time_seconds'].shift(-1)
    df['target_alert_next_hour'] = (df.groupby('camera_id')['security_alerts_count'].shift(-1) > 0).astype(int)
    
    # Eliminar filas con valores NaN resultantes de los rezagos
    df_clean = df.dropna().reset_index(drop=True)
    print(f"    - Registros sin valores nulos (NaNs): {df_clean.shape[0]} filas")
    
    # 4. Codificación One-Hot para el identificador de cámara (para que el modelo distinga perfiles)
    print("[*] Codificando variables de cámara (One-Hot Encoding)...")
    df_encoded = pd.get_dummies(df_clean, columns=['camera_id'], prefix='cam', drop_first=False)
    
    # Convertir booleanos de dummies a enteros 0/1 para entrenamiento
    cam_dummy_cols = [col for col in df_encoded.columns if col.startswith('cam_')]
    for col in cam_dummy_cols:
        df_encoded[col] = df_encoded[col].astype(int)
        
    print(f"    - Columnas de cámara codificadas: {cam_dummy_cols}")
    
    # 5. Definir variables predictoras
    features = [
        "hour", "day_of_week", "month", "is_weekend", "is_holiday", "is_promotion",
        "inflow_lag_1h", "inflow_lag_2h", "inflow_lag_24h", "inflow_rolling_mean_3h",
        "wait_lag_1h", "wait_lag_2h", "wait_lag_24h", "queue_lag_1h"
    ] + cam_dummy_cols
    
    # 6. División Cronológica (Split Temporal) por cámara
    # Para series de tiempo múltiples, dividimos las últimas fechas de cada cámara
    # En este caso, al estar ordenadas por cámara y luego fecha, dividimos el dataframe de forma cronológica por cámara.
    # Un enfoque robusto es dividir el dataframe codificado utilizando el 80% inicial de tiempo de cada cámara.
    
    train_dfs = []
    test_dfs = []
    
    for cam_val in df_clean['camera_id'].unique():
        cam_subset = df_encoded[df_encoded[f'cam_{cam_val}'] == 1]
        split_idx = int(len(cam_subset) * 0.8)
        
        train_dfs.append(cam_subset.iloc[:split_idx])
        test_dfs.append(cam_subset.iloc[split_idx:])
        
    train_df = pd.concat(train_dfs).sort_values(by='timestamp').reset_index(drop=True)
    test_df = pd.concat(test_dfs).sort_values(by='timestamp').reset_index(drop=True)
    
    X_train = train_df[features]
    X_test = test_df[features]
    
    print(f"    - Conjunto de entrenamiento: {X_train.shape[0]} muestras")
    print(f"    - Conjunto de prueba (evaluación): {X_test.shape[0]} muestras")
    
    # =====================================================================
    # MODELO 1: Predicción de Afluencia de Clientes
    # =====================================================================
    print("\n[*] Entrenando Modelo 1: Predicción de Afluencia de Shoppers (t+1)...")
    y_train_inflow = train_df['target_inflow_next_hour']
    y_test_inflow = test_df['target_inflow_next_hour']
    
    model_inflow = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model_inflow.fit(X_train, y_train_inflow)
    preds_inflow = model_inflow.predict(X_test)
    
    mae_inflow = mean_absolute_error(y_test_inflow, preds_inflow)
    rmse_inflow = np.sqrt(mean_squared_error(y_test_inflow, preds_inflow))
    r2_inflow = r2_score(y_test_inflow, preds_inflow)
    
    print("---------------------------------------------------------")
    print("MÉTRICAS MODELO 1 (Regresión de Afluencia):")
    print(f"  - Mean Absolute Error (MAE): {mae_inflow:.2f} personas")
    print(f"  - Root Mean Squared Error (RMSE): {rmse_inflow:.2f} personas")
    print(f"  - Coeficiente de Determinación R²: {r2_inflow:.4f}")
    print("---------------------------------------------------------")
    
    # =====================================================================
    # MODELO 2: Predicción Proactiva de Tiempos de Espera
    # =====================================================================
    print("\n[*] Entrenando Modelo 2: Predicción de Tiempo de Espera en Cajas (t+1)...")
    y_train_wait = train_df['target_wait_next_hour']
    y_test_wait = test_df['target_wait_next_hour']
    
    model_wait = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model_wait.fit(X_train, y_train_wait)
    preds_wait = model_wait.predict(X_test)
    
    mae_wait = mean_absolute_error(y_test_wait, preds_wait)
    rmse_wait = np.sqrt(mean_squared_error(y_test_wait, preds_wait))
    r2_wait = r2_score(y_test_wait, preds_wait)
    
    print("---------------------------------------------------------")
    print("MÉTRICAS MODELO 2 (Regresión de Tiempo de Espera):")
    print(f"  - Mean Absolute Error (MAE): {mae_wait:.2f} segundos")
    print(f"  - Root Mean Squared Error (RMSE): {rmse_wait:.2f} segundos")
    print(f"  - Coeficiente de Determinación R²: {r2_wait:.4f}")
    print("---------------------------------------------------------")
    
    # =====================================================================
    # MODELO 3: Clasificación del Riesgo de Alertas de Seguridad
    # =====================================================================
    print("\n[*] Entrenando Modelo 3: Probabilidad de Alertas de Seguridad (t+1)...")
    y_train_alert = train_df['target_alert_next_hour']
    y_test_alert = test_df['target_alert_next_hour']
    
    model_alert = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced", n_jobs=-1)
    model_alert.fit(X_train, y_train_alert)
    preds_alert = model_alert.predict(X_test)
    
    acc_alert = accuracy_score(y_test_alert, preds_alert)
    
    print("---------------------------------------------------------")
    print("MÉTRICAS MODELO 3 (Clasificación de Riesgo de Seguridad):")
    print(f"  - Exactitud (Accuracy): {acc_alert * 100.0:.2f}%")
    print("\nReporte de Clasificación Detallado:")
    print(classification_report(y_test_alert, preds_alert, target_names=["Sin Alerta", "Alerta Detectada"]))
    print("---------------------------------------------------------")
    
    # 7. Analizar la importancia de características
    print("\n[*] Analizando importancia de variables para predecir afluencia:")
    importances = model_inflow.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    for i in range(min(7, len(features))):
        print(f"    {i+1}. {features[indices[i]]}: {importances[indices[i]] * 100.0:.2f}% de relevancia")
        
    # Guardar los modelos entrenados y metadatos
    import joblib
    import json
    
    joblib.dump(model_inflow, os.path.join(SCRATCH_DIR, "model_inflow.joblib"))
    joblib.dump(model_wait, os.path.join(SCRATCH_DIR, "model_wait.joblib"))
    joblib.dump(model_alert, os.path.join(SCRATCH_DIR, "model_alert.joblib"))
    
    metadata = {
        "features": features,
        "cam_cols": cam_dummy_cols
    }
    with open(os.path.join(SCRATCH_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f)
        
    print("[*] Modelos y metadatos exportados a la carpeta scratch.")
        
    print("\n=========================================================")
    print("[+] Modelos de Machine Learning entrenados y validados con éxito.")
    print("=========================================================")


if __name__ == "__main__":
    train_retrovision_models()
