'use client';

import React from 'react';
import { DatePicker as AntDatePicker } from 'antd';
import dayjs, { Dayjs } from 'dayjs';

interface DatePickerProps {
  value: string;
  onChange: (date: string) => void;
  id?: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  minDate?: string;
  maxDate?: string;
  disabled?: boolean;
  [key: string]: any;
}

export function DatePicker({
  value,
  onChange,
  id,
  label,
  placeholder = '选择日期',
  required = false,
  minDate,
  maxDate = new Date().toISOString().split('T')[0],
  disabled = false,
  ...rest
}: DatePickerProps) {
  // Convert string to Dayjs for Ant Design
  const dateValue = value ? dayjs(value) : null;

  // Handle date change
  const handleChange = (date: Dayjs | null) => {
    if (date) {
      onChange(date.format('YYYY-MM-DD'));
    } else {
      onChange('');
    }
  };

  // Configure disabled dates
  const disabledDate = (current: Dayjs) => {
    if (!current) return false;

    if (minDate && current < dayjs(minDate)) return true;
    if (maxDate && current > dayjs(maxDate)) return true;

    return false;
  };

  return (
    <div>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <AntDatePicker
        id={id}
        value={dateValue}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        disabledDate={disabledDate}
        format="YYYY-MM-DD"
        className="w-full"
        style={{ width: '100%' }}
        size="large"
        {...rest}
      />
    </div>
  );
}

export { DatePicker as SimpleDatePicker };
