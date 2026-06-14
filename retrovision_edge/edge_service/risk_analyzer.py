"""
RetroVision Edge Service - Analizador de Riesgo

Módulo dedicado al análisis de comportamiento y cálculo de risk scores
basado en geometría de landmarks de MediaPipe.
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

import numpy as np

# MediaPipe Pose landmark indices
POSE_LANDMARKS = {
    "NOSE": 0,
    "LEFT_SHOULDER": 11,
    "RIGHT_SHOULDER": 12,
    "LEFT_WRIST": 15,
    "RIGHT_WRIST": 16,
    "LEFT_HIP": 23,
    "RIGHT_HIP": 24,
}

@dataclass
class RiskAnalysis:
    """Resultado del análisis de riesgo."""
    risk_score: float  # 0.0 to 1.0
    hidden_hands_score: float  # Manos ocultas/bolsillos
    abnormal_posture_score: float  # Inclinación anormal
    rules_triggered: List[str]  # Reglas que dispararon

class BehaviorAnalyzer:
    """
    Analizador de comportamiento basado en geometría de poses.
    
    Calcula un risk_score (0.0-1.0) analizando la posición relativa de
    landmarks de MediaPipe.
    """
    
    # Umbrales de distancia (normalizados respecto a altura del torso)
    HIDDEN_HANDS_DISTANCE_THRESHOLD = 0.45  # Si la mano está a menos del 45% del tamaño del torso
    ABNORMAL_POSTURE_THRESHOLD = 0.50  # Si la nariz sale del eje más de un 50%
    
    def __init__(self):
        """Inicializa el analizador de comportamiento."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("BehaviorAnalyzer inicializado (Versión Realista)")
    
    def analyze(
        self,
        landmarks: Optional[List[Tuple[float, float, float]]]
    ) -> RiskAnalysis:
        """Analiza landmarks y calcula un risk score."""
        analysis = RiskAnalysis(
            risk_score=0.0,
            hidden_hands_score=0.0,
            abnormal_posture_score=0.0,
            rules_triggered=[]
        )
        
        if not landmarks or len(landmarks) < 33:
            return analysis
        
        # Calcular scores por regla
        hidden_hands_score = self._check_hidden_hands(landmarks)
        abnormal_posture_score = self._check_abnormal_posture(landmarks)
        
        analysis.hidden_hands_score = hidden_hands_score
        analysis.abnormal_posture_score = abnormal_posture_score
        
        # Registrar reglas disparadas
        if hidden_hands_score > 0.6:
            analysis.rules_triggered.append("Manos Ocultas/Bolsillos")
        if abnormal_posture_score > 0.6:
            analysis.rules_triggered.append("Inclinacion/Agachamiento")
        
        # COMBINACIÓN CORREGIDA: Tomamos el RIESGO MÁXIMO, no un promedio diluido.
        # Así, si hace solo una cosa sospechosa, igual se dispara la alerta (> 0.7).
        combined_score = max(hidden_hands_score, abnormal_posture_score)
        analysis.risk_score = min(1.0, combined_score)
        
        return analysis
    
    def _check_hidden_hands(self, landmarks: List[Tuple[float, float, float]]) -> float:
        """Regla 1: Detecta manos ocultas cerca de la cintura."""
        try:
            left_wrist = landmarks[POSE_LANDMARKS["LEFT_WRIST"]]
            right_wrist = landmarks[POSE_LANDMARKS["RIGHT_WRIST"]]
            left_hip = landmarks[POSE_LANDMARKS["LEFT_HIP"]]
            right_hip = landmarks[POSE_LANDMARKS["RIGHT_HIP"]]
            left_shoulder = landmarks[POSE_LANDMARKS["LEFT_SHOULDER"]]
            
            # Usar tamaño del torso como referencia en lugar de la altura total
            # porque la cámara de retail a veces no ve las piernas completas.
            torso_height = abs(left_shoulder[1] - left_hip[1])
            if torso_height < 1.0: 
                return 0.0
            
            # Distancia de muñecas a caderas
            wrist_to_hip_left = np.sqrt((left_wrist[0] - left_hip[0])**2 + (left_wrist[1] - left_hip[1])**2)
            wrist_to_hip_right = np.sqrt((right_wrist[0] - right_hip[0])**2 + (right_wrist[1] - right_hip[1])**2)
            
            normalized_l = wrist_to_hip_left / torso_height
            normalized_r = wrist_to_hip_right / torso_height
            
            # Si ambas manos están cerca de los bolsillos/cintura
            if normalized_l < self.HIDDEN_HANDS_DISTANCE_THRESHOLD and normalized_r < self.HIDDEN_HANDS_DISTANCE_THRESHOLD:
                return 0.85 # Dispara la alarma (> 0.7)
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"Error en _check_hidden_hands: {e}")
            return 0.0
    
    def _check_abnormal_posture(self, landmarks: List[Tuple[float, float, float]]) -> float:
        """Regla 2: Detecta inclinación o agachamiento anormal."""
        try:
            nose = landmarks[POSE_LANDMARKS["NOSE"]]
            left_shoulder = landmarks[POSE_LANDMARKS["LEFT_SHOULDER"]]
            right_shoulder = landmarks[POSE_LANDMARKS["RIGHT_SHOULDER"]]
            left_hip = landmarks[POSE_LANDMARKS["LEFT_HIP"]]
            right_hip = landmarks[POSE_LANDMARKS["RIGHT_HIP"]]
            
            shoulder_center_x = (left_shoulder[0] + right_shoulder[0]) / 2
            shoulder_center_y = (left_shoulder[1] + right_shoulder[1]) / 2
            hip_center_y = (left_hip[1] + right_hip[1]) / 2
            
            torso_height = abs(hip_center_y - shoulder_center_y)
            if torso_height < 1.0:
                return 0.0
            
            # 1. ¿Se inclinó mucho hacia adelante/lados? (Nariz fuera del eje del cuerpo)
            horizontal_deviation = abs(nose[0] - shoulder_center_x)
            normalized_deviation = horizontal_deviation / torso_height
            
            # 2. ¿Se agachó? (Nariz demasiado cerca del nivel del pecho)
            vertical_distance = abs(shoulder_center_y - nose[1])
            normalized_vertical = vertical_distance / torso_height
            
            if normalized_deviation > self.ABNORMAL_POSTURE_THRESHOLD or normalized_vertical < 0.2:
                return 0.85 # Dispara la alarma (> 0.7)
            
            return 0.0
            
        except Exception as e:
            self.logger.debug(f"Error en _check_abnormal_posture: {e}")
            return 0.0