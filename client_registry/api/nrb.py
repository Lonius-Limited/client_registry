import frappe, requests, json
from datetime import datetime

class NRB():
    # def __init__(self):
    #     pass
    def __init__(self, pin_number, **kwargs):
        payload = kwargs
        settings = frappe.get_doc("Client Registry Settings")
        self.hie_url, self.hie_username, self.hie_password = settings.get("hie_url"), settings.get("hie_username"), settings.get_password("hie_password")
        self.identification_type = payload.get("identification_type")
        self.identification_number = payload.get("identification_number")
        self.agent = payload.get("agent")
        self.pin_number=pin_number
    def query_nrb(self):
        endpoint = "{}/nrb-ecitizen-api{}".format(self.hie_url, self.parse_params())
        print(endpoint)
        response = requests.get(endpoint, auth=(self.hie_username, self.hie_password))
        if response.status_code !=200 : frappe.throw("Error connecting to NRB Database")
        return response.json()
    def parse_params(self):
        param_template = "?id_number={}&type={}".format(self.identification_number,self.identification_type)
        #CAN BE: => citizen, alien, refugee
        return param_template
    def create_client(self, insert=True):
        exists = frappe.db.get_value("Client Registry",dict(identification_number=self.identification_number,identification_type = self.id_type_parser()),"name")
        if exists:
            doc = frappe.get_doc("Client Registry", exists)
            return doc.to_fhir()
        nrb_data =  self.query_nrb().get("data")
        date_string = nrb_data.get("date_of_birth").split(" ")[0] 
        date_format = "%Y-%m-%d"
        dob = datetime.strptime(date_string, date_format)
        gender = "Female"
        if nrb_data.get("sex") == "M" : gender ="Male"
        try:
            args = dict(
				doctype="Client Registry",
				first_name = nrb_data.get("first_name"),
				last_name = nrb_data.get("last_name"),
				middle_name = nrb_data.get("other_names") or "",
				gender = gender,
				date_of_birth = dob,
				# civil_status = nrb_data.get(""),
				# identification_residence = nrb_data.get("Place_of_Live", None),
				identification_type = self.id_type_parser(),
				identification_number = self.identification_number,
				citizenship = "KENYAN" if self.identification_type=="citizen" else "FOREIGN NATIONAL",
				place_of_birth = nrb_data.get("place_of_birth"),
                nrb_image =  nrb_data.get("photo"),
				pin_number = self.pin_number,
				agent = self.agent,

			)
            doc = frappe.get_doc(args).insert(ignore_permissions=1, ignore_mandatory=1)
            doc.add_comment('Comment', text="{}".format(json.dumps(nrb_data)))
            # self.parse_image(doc.get("name"), nrb_data=nrb_data)
            frappe.db.commit()
            return dict(total=1, result=[doc.to_fhir()])
        except Exception as e:
            frappe.throw("{}".format(e))
    def id_type_parser(self):
        id_type= self.identification_type
        if id_type=="citizen":
            return "National ID"
        elif id_type =="alien":
            return "Alien ID"
        else:
            return "Refugee ID"
    def parse_image(self, docname, nrb_data=None):
        from io import BytesIO
        if not nrb_data:
            nrb_data =  self.query_nrb().get("data")
        byte_string = nrb_data.get("photo")
       
        if not byte_string: return
        byte_stream = BytesIO(byte_string.encode())
        selfie_content = byte_stream.read()
        _filename = "{}-selfie.jpg".format(self.identification_number)
        print(_filename)
        with open(_filename, "wb") as f:
            f.write(byte_string.encode())
        selfie_ret = frappe.get_doc({
        "doctype": "File",
        "attached_to_doctype": 'Client Registry',#doctype,
        # "attached_to_name": docname,
        "attached_to_field": "client_passport_photo",
        # "folder": folder,
        "file_name": _filename,
        # "file_url": file_url,
        "is_private": 0,
        "content": selfie_content
       })
        selfie_ret.save(ignore_permissions=True)
        frappe.db.commit()
        
