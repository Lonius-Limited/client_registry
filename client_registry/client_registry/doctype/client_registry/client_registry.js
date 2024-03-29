// Copyright (c) 2022, Lonius Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Client Registry', {
	refresh: function (frm) {
		if (frm.doc.pin_number) {
			frm.add_custom_button(__("Show Password"), function () {
				//perform desired action such as routing to new form or fetching etc.
				frm.call('client_pin')
			},"Password Actions");
			frm.add_custom_button(__("Send PIN to SMS"), function () {
				//perform desired action such as routing to new form or fetching etc.
				frm.call('send_pin_to_phone')
			},"Password Actions");

		}
		frm.add_custom_button(__("Reset Password"), function(){
			//perform desired action such as routing to new form or fetching etc.
			frm.call('generate_pin').then(r=>{
				frm.call('client_pin')
				frm.reload_doc();
			})
		  }, __("Password Actions"));

		 
		  frm.add_custom_button(__("Verify Biometrics"), function(){
			//perform desired action such as routing to new form or fetching etc.
			frm.call('image_rekognition_match').then(r=>{
				// frm.call('client_pin')
				frm.reload_doc();
			})
		  },);

		  //image_rekognition_match
		  //NRB Maneno
		  frm.add_custom_button(__("Rerun Biometrics"), function(){
			//perform desired action such as routing to new form or fetching etc.
			frm.call('iprs_search').then(r=>{
				// frm.call('client_pin')
				console.log(r)
			})
		  },);
	},
	
});
