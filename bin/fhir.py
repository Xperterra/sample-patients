import datetime
from allergy import Allergy
from clinicalnote import ClinicalNote
from patient import Patient
from med import Med
from problem import Problem
from procedure import Procedure
from refill import Refill
from lab import Lab
from immunization import Immunization
from vitals import VitalSigns
from document import Document
from familyhistory import FamilyHistory
from socialhistory import SocialHistory
from imagingstudy import ImagingStudy
from testdata import NOTES_PATH
from testdata import DOCUMENTS_PATH
from vitalspatientgenerator import generate_patient
from docs import fetch_document
import os
import uuid

from jinja2 import Environment, FileSystemLoader
template_env = Environment(loader=FileSystemLoader('fhir_templates'), autoescape=True)

SMOKINGCODES = {
    '428041000124106': 'Current some day smoker',
    '266919005': 'Never smoker',
    '449868002': 'Current every day smoker',
    '266927001': 'Unknown if ever smoked',
    '8517006': 'Former smoker'
}

base=0
def uid(resource_type=None, id=None):
    global base
    if not id:
        base += 1
        id = base
    if (resource_type == None):
      return str(id)
    else:
      return "%s/%s"%(resource_type, str(id))

def getVital(v, vt, encounter_id):
  return {
    'id': v.id,
    'date': v.timestamp[:10],
    'code': vt['uri'].split('/')[-1],
    'encounter_id': encounter_id,
    'units': vt['unit'],
    'value': float(getattr(v, vt['name'])),
    'scale': 'Qn',
    'name': vt['name']
    }

class FHIRSamplePatient(object):
  def __init__(self, pid, path, base_url=""):
    self.path = path
    self.pid = pid

    if len(base_url) > 0 and not base_url.endswith("/"):
        base_url += "/"

    self.base_url = base_url

    return

  def writePatientData(self):

    pfile = open(os.path.join(self.path, "patient-%s.fhir-bundle.xml"%self.pid), "w")
    p = Patient.mpi[self.pid]

    now = datetime.datetime.now().isoformat()
    base_url = self.base_url

    if self.pid == '99912345':
        vpatient = generate_patient()
        p.dob = vpatient["birthday"]
        VitalSigns.loadVitalsPatient(vpatient)

    print >>pfile, """<?xml version="1.0" encoding="UTF-8"?>
<Bundle xmlns="http://hl7.org/fhir">
    <type value="transaction"/>
"""

    if self.pid in Document.documents:
        for d in [doc for doc in Document.documents[self.pid] if doc.type == 'photograph']:
            data = fetch_document (self.pid, d.file_name)
            d.content = data['base64_content']
            d.size = data['size']
            d.hash = data['hash']
            b = d
            id = uid("Binary", "%s-photo" % d.id)
            d.binary_id = id
            template = template_env.get_template('binary.xml')
            print >>pfile, template.render(dict(globals(), **locals()))
            p.photo_code = d.mime_type
            p.photo_binary_id = d.binary_id
            p.photo_size = d.size
            p.photo_hash = d.hash
            p.photo_title = d.title

    id = "Patient/%s"%self.pid
    pid = id
    template = template_env.get_template('patient.xml')
    print >>pfile, template.render(dict(globals(), **locals()))

    bps = []
    othervitals = []

    if self.pid in VitalSigns.vitals:
      encounters = []
      for v in  VitalSigns.vitals[self.pid]:
          encounter_id = None
          e = [i for i in encounters if i['date'] == v.start_date and i['type'] == v.encounter_type]
          if len(e) > 0:
              encounter_id = e[0]['id']
          else:
              encounter_id = uid("Encounter", v.id)
              encounters.append ({'date': v.start_date, 'type': v.encounter_type, 'id': encounter_id})
              id = encounter_id
              template = template_env.get_template('encounter.xml')
              print >>pfile, template.render(dict(globals(), **locals()))
          for vt in VitalSigns.vitalTypes:
              try:
                  othervitals.append(getVital(v, vt, encounter_id))
              except: pass
          try:
              systolic = getVital(v, VitalSigns.systolic, encounter_id)
              diastolic = getVital(v, VitalSigns.diastolic, encounter_id)
              bp = systolic
              bp['systolic'] = int(systolic['value'])
              bp['diastolic'] = int(diastolic['value'])
              bp['site'] = v.bp_site
              bp['id'] = v.id
              if bp['site']:
                for pc in VitalSigns.bpPositionCodes:
                    if pc['name'] == bp['site']:
                        bp['site_code'] = pc['code']
                        bp['site_system'] = pc['system']
              bp['method'] = v.bp_method
              if bp['method']:
                for pc in VitalSigns.bpPositionCodes:
                    if pc['name'] == bp['method']:
                        bp['method_code'] = pc['code']
                        bp['method_system'] = pc['system']
              bp['position'] = v.bp_position
              if bp['position']:
                for pc in VitalSigns.bpPositionCodes:
                    if pc['name'] == bp['position']:
                        bp['position_code'] = pc['code']
                        bp['position_system'] = pc['system']
              bps.append(bp)
          except: pass

    for bp in bps:
        systolicid = uid("Observation", "%s-systolic" % bp['id'])
        diastolicid = uid("Observation", "%s-diastolic" % bp['id'])
        id = uid("Observation", "%s-bp" % bp['id'])
        template = template_env.get_template('blood_pressure.xml')
        print >>pfile, template.render(dict(globals(), **locals()))

        id = systolicid
        o = {
                "date": bp['date'],
                "code": "8480-6",
                "name": "Systolic blood pressure",
                "scale": "Qn",
                "value": bp['systolic'],
                "units": "mm[Hg]",
                "unitsCode": "mm[Hg]",
                "categoryCode": "vital-signs",
                "categoryDisplay": "Vital Signs"
        }
        template = template_env.get_template('observation.xml')
        print >>pfile, template.render(dict(globals(), **locals()))

        id = diastolicid
        o = {
                "date": bp['date'],
                "code": "8462-4",
                "name": "Diastolic blood pressure",
                "scale": "Qn",
                "value": bp['diastolic'],
                "units": "mm[Hg]",
                "unitsCode": "mm[Hg]",
                "categoryCode": "vital-signs",
                "categoryDisplay": "Vital Signs"
        }
        template = template_env.get_template('observation.xml')
        print >>pfile, template.render(dict(globals(), **locals()))

    template = template_env.get_template('observation.xml')
    for o in othervitals:
        id = uid("Observation", '-'.join((o["id"], o["name"].lower().replace(' ', '').replace('_', ''))))
        if "units" in o.keys():
           o["unitsCode"] = o["units"]
           o["categoryCode"] = "vital-signs"
           o["categoryDisplay"] = "Vital Signs"
        print >>pfile, template.render(dict(globals(), **locals()))

    if self.pid in Lab.results:
      for o in Lab.results[self.pid]:
        id = uid("Observation", "%s-lab" % o.id)
        o.categoryCode = "laboratory"
        o.categoryDisplay = "Laboratory"
        print >>pfile, template.render(dict(globals(), **locals()))

    medtemplate = template_env.get_template('medication.xml')
    dispensetemplate = template_env.get_template('medication_dispense.xml')
    if self.pid in Med.meds:
      for m in Med.meds[self.pid]:
        medid = id = uid("MedicationOrder", m.id)
        print >>pfile, medtemplate.render(dict(globals(), **locals()))

        for f in Refill.refill_list(m.pid, m.rxn):
          id = uid("MedicationDispense", f.id)
          print >>pfile, dispensetemplate.render(dict(globals(), **locals()))

    template = template_env.get_template('condition.xml')
    if self.pid in Problem.problems:
      for c in Problem.problems[self.pid]:
        id = uid("Condition", c.id)
        print >>pfile, template.render(dict(globals(), **locals()))

    template = template_env.get_template('procedure.xml')
    if self.pid in Procedure.procedures:
      for w in Procedure.procedures[self.pid]:
        id = uid("Procedure", w.id)
        print >>pfile, template.render(dict(globals(), **locals()))

    template = template_env.get_template('immunization.xml')
    if self.pid in Immunization.immunizations:
      for i in Immunization.immunizations[self.pid]:
        id = uid("Immunization", i.id)
        i.cvx_system, i.cvx_id = i.cvx.rsplit("cvx",1)
        i.cvx_system += "cvx"
        print >>pfile, template.render(dict(globals(), **locals()))

    template = template_env.get_template('family_history.xml')
    if self.pid in FamilyHistory.familyHistories:
      for fh in FamilyHistory.familyHistories[self.pid]:
        id = uid("FamilyHistory", fh.id)
        print >>pfile, template.render(dict(globals(), **locals()))

    template = template_env.get_template('smoking_status.xml')
    if self.pid in SocialHistory.socialHistories:
        t = SocialHistory.socialHistories[self.pid]
        t.smokingStatusText = SMOKINGCODES[t.smokingStatusCode]
        id = uid("Observation", '-'.join((t.id,"smokingstatus")))
        print >>pfile, template.render(dict(globals(), **locals()))

    if p.gestage:
        template = template_env.get_template('observation.xml')
        o = {
            "date": p.dob,
            "code": "18185-9",
            "name": "Gestational age at birth",
            "scale": "Qn",
            "value": p.gestage,
            "units": "weeks",
            "unitsCode": "wk",
            "categoryCode": "exam",
            "categoryDisplay": "Exam"
        }
        id = uid("Observation", "%s-gestage" % self.pid)
        print >>pfile, template.render(dict(globals(), **locals()))

    if self.pid in Allergy.allergies:
        for al in Allergy.allergies[self.pid]:
            if al.statement == 'positive':
                if al.type == 'drugClass':
                    al.typeDescription = 'medication'
                    al.system = "http://rxnav.nlm.nih.gov/REST/Ndfrt"
                elif al.type == 'drug':
                    al.typeDescription = 'medication'
                    al.system = "http://www.nlm.nih.gov/research/umls/rxnorm"
                elif al.type == 'food':
                    al.typeDescription = 'food'
                    al.system = "http://fda.gov/UNII/"
                elif al.type == 'environmental':
                    al.typeDescription = 'environment'
                    al.system = "http://fda.gov/UNII/"
                if al.reaction:
                    if al.severity.lower() == 'mild':
                        al.severity = 'mild'
                        al.criticality = 'CRITL'
                    elif al.severity.lower() == 'severe':
                        al.severity = 'severe'
                        al.criticality = 'CRITH'
                    elif al.severity.lower() == 'life threatening' or al.severity.lower() == 'fatal':
                        al.severity = 'severe'
                        al.criticality = 'CRITH'
                    elif al.severity.lower() == 'moderate':
                        al.severity = 'moderate'
                        al.criticality = 'CRITU'
                    else:
                        al.severity = None
                id = uid("AllergyIntolerance", al.id)
                template = template_env.get_template('allergy.xml')
                print >>pfile, template.render(dict(globals(), **locals()))
            elif al.statement == 'negative' and al.type == 'general':
                if al.code == '160244002':
                    template = template_env.get_template('no_known_allergies.xml')
                    id = uid("List", al.id)
                    al.loinc_code = '52473-6'
                    al.loinc_display = 'Allergy'
                    al.text = 'No known allergies'
                    print >>pfile, template.render(dict(globals(), **locals()))
                elif al.code == '409137002':
                    template = template_env.get_template('no_known_allergies.xml')
                    id = uid("List", al.id)
                    al.loinc_code = '11382-9'
                    al.loinc_display = 'Medication allergy'
                    al.text = 'No known history of drug allergy'
                    print >>pfile, template.render(dict(globals(), **locals()))
                else:
                    template = template_env.get_template('general_observation.xml')
                    o = {
                        "date": al.start,
                        "system": "http://snomed.info/sct",
                        "code": al.code,
                        "name": al.allergen,
                        "categoryCode": "exam",
                        "categoryDisplay": "Exam"
                    }
                    id = uid("Observation", "%s-allergy" % al.id)
                    print >>pfile, template.render(dict(globals(), **locals()))

    addedPractitioner = False

    if self.pid in ClinicalNote.clinicalNotes:
        id = 'Practitioner/1234'
        template = template_env.get_template('practitioner.xml')
        print >>pfile, template.render(dict(globals(), **locals()))
        addedPractitioner = True
        for d in ClinicalNote.clinicalNotes[self.pid]:
            if d.mime_type == 'text/plain':
                data = fetch_document (self.pid, d.file_name)
                d.content = data['base64_content']
                b = d
                id = uid("Binary", "%s-note" % d.id)
                d.binary_id = id
                template = template_env.get_template('binary.xml')
                print >>pfile, template.render(dict(globals(), **locals()))
                id = uid("DocumentReference", "%s-note" % d.id)
                d.system = "http://loinc.org"
                d.code = '34109-9'
                d.display = 'Note'
                template = template_env.get_template('document.xml')
                print >>pfile, template.render(dict(globals(), **locals()))

    if self.pid in Document.documents:
        if not addedPractitioner:
            id = 'Practitioner/1234'
            template = template_env.get_template('practitioner.xml')
            print >>pfile, template.render(dict(globals(), **locals()))
        for d in [doc for doc in Document.documents[self.pid] if doc.type != 'photograph']:
            data = fetch_document (self.pid, d.file_name)
            d.content = data['base64_content']
            d.size = data['size']
            d.hash = data['hash']
            b = d
            id = uid("Binary", "%s-document" % d.id)
            d.binary_id = id
            template = template_env.get_template('binary.xml')
            print >>pfile, template.render(dict(globals(), **locals()))
            id = uid("DocumentReference", "%s-document" % d.id)
            d.system = 'http://smarthealthit.org/terms/codes/DocumentType#'
            d.code = d.type
            d.display = d.type
            template = template_env.get_template('document.xml')
            print >>pfile, template.render(dict(globals(), **locals()))

    if self.pid in ImagingStudy.imagingStudies:
        st = {}
        for img in ImagingStudy.imagingStudies[self.pid]:
            data = fetch_document (self.pid, img.image_file_name)
            img.mime_type = "application/dicom"
            img.content = data['base64_content']
            img.size = data['size']
            img.hash = data['hash']
            b = img
            id = uid("Binary", "%s-dicom" % img.id)
            img.binary_id = id
            template = template_env.get_template('binary.xml')
            print >>pfile, template.render(dict(globals(), **locals()))
            if img.study_oid not in st.keys():
                st[img.study_oid] = {
                    'id': img.id,
                    'title': img.study_title,
                    'date': img.study_date,
                    'accession_number': img.study_accession_number,
                    'modality': img.study_modality,
                    'oid': img.study_oid,
                    'series_count': 0,
                    'images_count': 0,
                    'series': {}
                }
            series = st[img.study_oid]['series']
            if img.series_oid not in series.keys():
                st[img.study_oid]['series_count'] += 1
                series[img.series_oid] = {
                    'number': st[img.study_oid]['series_count'],
                    'title': img.series_title,
                    'oid': img.series_oid,
                    'images_count': 0,
                    'images': []
                }
            st[img.study_oid]['images_count'] += 1
            series[img.series_oid]['images_count'] += 1
            series[img.series_oid]['images'].append({
                'title': img.image_title,
                'date': img.image_date,
                'file_name': img.image_file_name,
                'oid': img.image_oid,
                'binary_id': img.binary_id,
                'sop': img.image_sop,
                'number': series[img.series_oid]['images_count']
            })


        for i in st:
            s = st[i]
            id = uid("ImagingStudy", s['id'])
            template = template_env.get_template('imagingstudy.xml')
            print >>pfile, template.render(dict(globals(), **locals()))

    print >>pfile, "\n</Bundle>"
    pfile.close()
