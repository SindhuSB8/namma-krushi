"""Specific, knowledge-base-grounded adjustment advice for each abnormal reading.

The text follows the Namma Krushi knowledge base (temperature/humidity/
ventilation, light/CO2/air movement, irrigation/soil moisture).  It tells the
farmer what to check or change for the one parameter that is out of range; it
does not invent numeric set-points beyond the model's own labeling policy.
"""

ADVICE = {
    ("temperature", "High"): (
        "Temperature is above the suitable range. Open vents or improve ventilation, shade during peak radiation, and check that irrigation timing is not leaving the house hot and humid.",
        "ತಾಪಮಾನ ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಹೆಚ್ಚಿದೆ. ವೆಂಟ್‌ಗಳನ್ನು ತೆರೆದು ಗಾಳಿಯಾಡುವಿಕೆ ಹೆಚ್ಚಿಸಿ, ಹೆಚ್ಚು ಬಿಸಿಲಿನ ಸಮಯದಲ್ಲಿ ನೆರಳು ನೀಡಿ, ಮತ್ತು ನೀರಾವರಿ ಸಮಯವನ್ನು ಪರಿಶೀಲಿಸಿ.",
    ),
    ("temperature", "Low"): (
        "Temperature is below the suitable range. Recheck where the sensor is placed, review night-time temperatures, and avoid cold draughts straight from the vents; growth and fruit set may slow.",
        "ತಾಪಮಾನ ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಕಡಿಮೆ ಇದೆ. ಸಂವೇದಕದ ಸ್ಥಾನವನ್ನು ಮರುಪರಿಶೀಲಿಸಿ, ರಾತ್ರಿಯ ತಾಪಮಾನ ಗಮನಿಸಿ, ವೆಂಟ್‌ಗಳಿಂದ ತಣ್ಣನೆಯ ಗಾಳಿ ನೇರವಾಗಿ ಬರುವುದನ್ನು ತಪ್ಪಿಸಿ; ಬೆಳವಣಿಗೆ ಮತ್ತು ಕಾಯಿ ಕಟ್ಟುವಿಕೆ ನಿಧಾನವಾಗಬಹುದು.",
    ),
    ("humidity", "High"): (
        "Humidity is above the suitable range, which favours leaf diseases. Improve air movement and ventilation, remove unnecessary lower or diseased leaves, and avoid wetting foliage late in the day or over-irrigating.",
        "ಆರ್ದ್ರತೆ ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಹೆಚ್ಚಿದೆ; ಇದು ಎಲೆ ರೋಗಗಳಿಗೆ ಅನುಕೂಲಕರ. ಗಾಳಿಯಾಡುವಿಕೆ ಹೆಚ್ಚಿಸಿ, ಅನಗತ್ಯ ಕೆಳ ಎಲೆಗಳು ಅಥವಾ ರೋಗಪೀಡಿತ ಎಲೆಗಳನ್ನು ತೆಗೆಯಿರಿ, ಸಂಜೆ ಎಲೆಗಳನ್ನು ಒದ್ದೆ ಮಾಡುವುದು ಮತ್ತು ಅತಿಯಾದ ನೀರಾವರಿ ತಪ್ಪಿಸಿ.",
    ),
    ("humidity", "Low"): (
        "Humidity is below the suitable range. Recheck the sensor, confirm the root zone is not dry, and look at temperature and ventilation together, since hot, strongly ventilated air dries the house.",
        "ಆರ್ದ್ರತೆ ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಕಡಿಮೆ ಇದೆ. ಸಂವೇದಕವನ್ನು ಮರುಪರಿಶೀಲಿಸಿ, ಬೇರು ವಲಯ ಒಣಗಿಲ್ಲವೆಂದು ಖಚಿತಪಡಿಸಿ, ತಾಪಮಾನ ಮತ್ತು ಗಾಳಿಯಾಡುವಿಕೆಯನ್ನು ಒಟ್ಟಾಗಿ ಪರಿಶೀಲಿಸಿ.",
    ),
    ("soil_moisture", "High"): (
        "Root-zone moisture is above the suitable range. Reduce irrigation frequency, check drainage and standing water, and watch for brown roots or wilting even though the medium is wet.",
        "ಬೇರು ವಲಯದ ತೇವಾಂಶ ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಹೆಚ್ಚಿದೆ. ನೀರಾವರಿ ಆವರ್ತನ ಕಡಿಮೆ ಮಾಡಿ, ಒಳಚರಂಡಿ ಮತ್ತು ನಿಂತ ನೀರನ್ನು ಪರಿಶೀಲಿಸಿ; ಮಾಧ್ಯಮ ಒದ್ದೆಯಿದ್ದರೂ ಗಿಡ ಬಾಡುತ್ತಿದ್ದರೆ ಅಥವಾ ಬೇರು ಕಂದಾಗಿದ್ದರೆ ಗಮನಿಸಿ.",
    ),
    ("soil_moisture", "Low"): (
        "Root-zone moisture is below the suitable range. Check that emitters are flowing and drainage works, and confirm the reading suits your growing medium before changing the schedule; avoid severe drying followed by heavy watering.",
        "ಬೇರು ವಲಯದ ತೇವಾಂಶ ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಕಡಿಮೆ ಇದೆ. ಡ್ರಿಪ್ ಎಮಿಟರ್‌ಗಳಲ್ಲಿ ನೀರು ಬರುತ್ತಿದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸಿ; ವೇಳಾಪಟ್ಟಿ ಬದಲಿಸುವ ಮೊದಲು ಈ ಓದು ನಿಮ್ಮ ಬೆಳವಣಿಗೆ ಮಾಧ್ಯಮಕ್ಕೆ ಸರಿಹೊಂದುತ್ತದೆಯೇ ಎಂದು ಖಚಿತಪಡಿಸಿ; ಒಣಗಿಸಿ ನಂತರ ಹೆಚ್ಚು ನೀರು ಹಾಕುವುದನ್ನು ತಪ್ಪಿಸಿ.",
    ),
    ("light_intensity", "High"): (
        "Light is above the suitable range. Use shade net or screens during peak sun and read it together with temperature, since strong light plus heat can cause stress and sunscald.",
        "ಬೆಳಕು ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಹೆಚ್ಚಿದೆ. ಹೆಚ್ಚು ಬಿಸಿಲಿನ ಸಮಯದಲ್ಲಿ ಶೇಡ್ ನೆಟ್ ಬಳಸಿ; ಹೆಚ್ಚು ಬೆಳಕು ಮತ್ತು ಶಾಖ ಒಟ್ಟಿಗೆ ಇದ್ದರೆ ಗಿಡಕ್ಕೆ ಒತ್ತಡ ಮತ್ತು ಬಿಸಿಲಿನ ಸುಟ್ಟ ಗುರುತು ಆಗಬಹುದು.",
    ),
    ("light_intensity", "Low"): (
        "Light is below the suitable range. Clean the cover, check for shade from structures or a dense canopy, and make sure this is not simply a cloudy or evening reading.",
        "ಬೆಳಕು ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಕಡಿಮೆ ಇದೆ. ಹೊದಿಕೆಯನ್ನು ಸ್ವಚ್ಛಗೊಳಿಸಿ, ರಚನೆ ಅಥವಾ ದಟ್ಟ ಎಲೆಗಳಿಂದ ನೆರಳಾಗುತ್ತಿದೆಯೇ ಪರಿಶೀಲಿಸಿ, ಮೋಡ ಅಥವಾ ಸಂಜೆಯ ಓದು ಅಲ್ಲವೆಂದು ಖಚಿತಪಡಿಸಿ.",
    ),
    ("co2", "High"): (
        "CO₂ is above the suitable range. Increase ventilation to bring in outside air, check the sensor and any enrichment equipment, and make sure people can work safely.",
        "CO₂ ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಹೆಚ್ಚಿದೆ. ಹೊರಗಿನ ಗಾಳಿ ಬರುವಂತೆ ಗಾಳಿಯಾಡುವಿಕೆ ಹೆಚ್ಚಿಸಿ, ಸಂವೇದಕ ಮತ್ತು CO₂ ಸಾಧನ ಇದ್ದರೆ ಅದನ್ನು ಪರಿಶೀಲಿಸಿ; ಕೆಲಸಗಾರರ ಸುರಕ್ಷತೆ ಖಚಿತಪಡಿಸಿ.",
    ),
    ("co2", "Low"): (
        "CO₂ is below the suitable range. In a closed house CO₂ falls during active photosynthesis and ventilation replenishes it. Recheck the sensor and do not add CO₂ without a controlled system.",
        "CO₂ ಸೂಕ್ತ ಶ್ರೇಣಿಗಿಂತ ಕಡಿಮೆ ಇದೆ. ಮುಚ್ಚಿದ ಮನೆಯಲ್ಲಿ ದ್ಯುತಿಸಂಶ್ಲೇಷಣೆಯ ಸಮಯದಲ್ಲಿ CO₂ ಕಡಿಮೆಯಾಗುತ್ತದೆ; ಗಾಳಿಯಾಡುವಿಕೆ ಅದನ್ನು ತುಂಬುತ್ತದೆ. ಸಂವೇದಕ ಪರಿಶೀಲಿಸಿ; ನಿಯಂತ್ರಿತ ವ್ಯವಸ್ಥೆ ಇಲ್ಲದೆ CO₂ ಸೇರಿಸಬೇಡಿ.",
    ),
}

# Knowledge-base articles each piece of advice comes from.
SOURCE_DOCUMENTS = {
    "temperature": "05_temperature_humidity_and_ventilation",
    "humidity": "05_temperature_humidity_and_ventilation",
    "soil_moisture": "07_irrigation_and_soil_moisture",
    "light_intensity": "06_light_co2_and_air_movement",
    "co2": "06_light_co2_and_air_movement",
}


def advice_for(feature, direction, language="English"):
    pair = ADVICE.get((feature, direction))
    if not pair:
        return ""
    return pair[1] if language == "Kannada" else pair[0]
