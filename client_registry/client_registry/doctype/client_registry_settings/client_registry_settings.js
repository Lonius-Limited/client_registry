// Copyright (c) 2024, Lonius Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Client Registry Settings', {
	onload: function (frm) {
		frm.get_field("blacklisted_fields").grid.cannot_add_rows = true;
		frm.refresh_field('blacklisted_fields');

		// frappe.msgprint("I am adding fields")
		const method = "client_registry.client_registry.doctype.client_registry_settings.client_registry_settings.all_client_registry_fields";
		const freeze = true;
		const freeze_message = "Please wait as we update fields";
		frappe.call({ method }).then(r => {
			
			let currentFields = frm.doc.blacklisted_fields.map(x => x.field_name);
			const docFields = r.message
			console.log("We got: ",docFields)
			console.log(currentFields)
			const missingFields = docFields.filter(x => !currentFields.includes(x))
			console.log("Missing Fields: ",missingFields)
			if (missingFields.length>0) {
				for (let i = 0; i < missingFields.length; i++) {
					// console.log("Uh")
					 frm.add_child('blacklisted_fields', {
						field_name: missingFields[i],
						blacklisted: 0
					});
				}
				frm.refresh_field('blacklisted_fields');
				frm.save()
			}

		})
	}
});
frappe.ui.form.on('Blacklisted Fields', {
	blacklisted_fields_add(frm, cdt, cdn) {
		frappe.msgprint("I am adding")
	}
})