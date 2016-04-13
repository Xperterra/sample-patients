import json

cmp_report = {
  "resourceType": "DiagnosticReport",
  "id": "argonaut-lab-report-1",
  "status": "final",
  "subject": {
    "reference": "Patient/1032702"
  },
  "effectiveDateTime": "2005-07-04",
  "issued": "2005-07-06T11:45:33+11:00",
  "category": {
  "coding": [{
    "system": "http://hl7.org/fhir/v2/0074",
    "code": "CH",
    "display": "Chemistry"}]
    },
  "code": {
   "coding": [{
    "system": "http://loinc.org",
    "code": "24323-8",
    "display": "Comprehensive metabolic 2000 panel - Serum or Plasma"}]
  },
  "result": []
}

cbc_report = {
  "resourceType": "DiagnosticReport",
  "id": "argonaut-lab-report-2",
    "status": "final",
    "category": {
    "subject": {
      "reference": "Patient/1032702"
    },
  "effectiveDateTime": "2005-07-04",
  "issued": "2005-07-06T11:45:33+11:00",
      "coding": [{
        "system": "http://hl7.org/fhir/v2/0074",
        "code": "HM",
        "display": "Hematology"}]
    },
    "code": {
      "coding": [{
        "system": "http://loinc.org",
        "code": "58410-2",
        "display": "Complete blood count (hemogram) panel - Blood by Automated count"}]
    },
  "result": []
}


analytes = """
Sodium	2951-2	mmol/L
Potassium	2823-3	mmol/L
Chloride	2075-0	mmol/L
Carbon dioxide, total	2028-9	mmol/L
Blood urea nitrogen	3094-0	mg/dL
Creatinine	2160-0	mg/dL
Glucose	2345-7	mg/dL
Calcium	17861-6	mg/dL
Protein	2885-2	g/dL
Albumin	1751-7	g/dL
Total Bilirubin	1975-2	mg/dL
Alkaline phosphatase	6768-6	U/L
Alanine aminotransferase	1742-6	mmol/L
Aspartate aminotransferase	1920-8	mmol/L
""".split("\n")[1:-1]

values =[
  138,
  3.5,
  102,
  25,
  9,
  1.1,
  82,
  9.5,
  7.2,
  4.2,
  1.1,
  72,
  18,
  12
]

obs_count = 0

resources = [cmp_report, cbc_report]

def id_of(r):
    return r['resourceType'] + "/" + r['id']

def lab_observation(v, a):
    global obs_count
    obs_count += 1
    return {
      "resourceType": "Observation",
      "id": "argonaut-lab-%s"%(obs_count),
      "text": {
        "status": "generated",
        "div": "<div>See structured data</div>"
      },
      "status": "final",
      "category": {
        "coding": [
          {
            "system": "http://hl7.org/fhir/observation-category",
            "code": "laboratory",
            "display": "Laboratory"
          }
        ],
        "text": "Laboratory"
      },
      "code": {
        "coding": [
          {
            "system": "http://loinc.org",
            "code": a[1],
            "display": a[0]
          }
        ],
        "text": a[0]
      },
      "subject": {
        "reference": "Patient/1032702"
      },
      "effectiveDateTime": "2005-07-04",
      "valueQuantity": {
        "value": v,
        "unit": a[2],
        "system": "http://unitsofmeasure.org"
      }        
    }

for o in [lab_observation(values[i], a.split("\t")) for i, a in enumerate(analytes)]:
  resources.append(o)
  cmp_report['result'].append({
    'reference': 'Observation/' + o['id']          
  })



analytes = """
Leukocytes	6690-2	10*3/uL
Erythrocytes	789-8	10*6/uL
Hemoglobin	718-7	g/dL
Hematocrit	4544-3	%
Erythrocyte mean corpuscular volume	787-2	fL
Erythrocyte mean corpuscular hemoglobin	785-6	pg
Erythrocyte mean corpuscular hemoglobin concentration	786-4	g/dL
Erythrocyte distribution width [Ratio]	788-0	%
Platelets	777-3	10*3/uL
Platelet mean volume	32623-1	fL
""".split("\n")[1:-1]

values =[
  7.6,
  5.2,
  17.2,
  49,
  92,
  29,
  34.2,
  11.8,
  370,
  9.1,
]

for o in [lab_observation(values[i], a.split("\t")) for i, a in enumerate(analytes)]:
  resources.append(o)
  cbc_report['result'].append({
    'reference': 'Observation/' + o['id']          
  })

    
print(json.dumps({
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [{'resource': r, 'request': {'method': 'PUT', 'url': id_of(r)}} for r in resources]
}, indent=2))
