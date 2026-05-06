import React from "react";
import DatePicker, { registerLocale } from "react-datepicker";
import fi from "date-fns/locale/fi";
import "react-datepicker/dist/react-datepicker.css";

registerLocale("fi", fi);

function DatePickerField({ label, value, onChange, labelStyle, inputStyle }) {
  const selected = value ? new Date(value) : null;

  const handleChange = (date) => {
    if (date) {
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, "0");
      const dd = String(date.getDate()).padStart(2, "0");
      onChange(`${yyyy}-${mm}-${dd}`);
    } else {
      onChange("");
    }
  };

  return (
    <div>
      {label && <label style={labelStyle}>{label}</label>}
      <DatePicker
        selected={selected}
        onChange={handleChange}
        locale="fi"
        dateFormat="dd.MM.yyyy"
        placeholderText="Valitse päivä..."
        isClearable
        showWeekNumbers
        todayButton="Tänään"
        customInput={
          <input
            style={{
              ...inputStyle,
              width: "100%",
              cursor: "pointer"
            }}
            readOnly
          />
        }
      />
    </div>
  );
}

export default DatePickerField;