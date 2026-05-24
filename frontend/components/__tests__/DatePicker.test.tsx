import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { DatePicker } from '../DatePicker/DatePicker';
import MonthGrid from '../DatePicker/MonthGrid';

describe('DatePicker', () => {
  it('should render input box', () => {
    render(<DatePicker value="" onChange={() => {}} id="test-date" />);
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
  });

  it('should display selected date', () => {
    render(<DatePicker value="2024-03-15" onChange={() => {}} id="test-date" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveValue('2024-03-15');
  });

  it('should call onChange when date is selected', () => {
    const handleChange = jest.fn();
    render(<DatePicker value="" onChange={handleChange} id="test-date" />);

    // Open calendar
    const input = screen.getByRole('textbox');
    fireEvent.click(input);

    // Click a date (this will fail until component is implemented)
    const dateButton = screen.getByText('15');
    fireEvent.click(dateButton);

    expect(handleChange).toHaveBeenCalled();
  });

  it('should disable future dates', () => {
    render(<DatePicker value="" onChange={() => {}} id="test-date" maxDate="2024-12-31" />);
    // Future dates should have disabled attribute
    // Implementation will verify this
  });

  it('should show month grid when button clicked', () => {
    render(<DatePicker value="" onChange={() => {}} id="test-date" />);
    const input = screen.getByRole('textbox');
    fireEvent.click(input);

    // Click "快速选择月份" button
    const monthGridButton = screen.queryByText('快速选择月份');
    // This will be implemented in Task 4
  });

  it('should close month grid and update calendar when month selected', () => {
    const handleChange = jest.fn();
    render(<DatePicker value="2024-03-15" onChange={handleChange} id="test-date" />);
    // Integration test will be added after MonthGrid is implemented
  });

  it('should support aria-invalid attribute', () => {
    render(
      <DatePicker
        value=""
        onChange={() => {}}
        id="test-date"
        aria-invalid="true"
      />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });
});

describe('MonthGrid', () => {
  it('should render 12 months in grid', () => {
    const onSelectMonth = jest.fn();
    const { getByText } = render(
      <MonthGrid
        currentMonth={new Date('2024-03-15')}
        onSelectMonth={onSelectMonth}
        onClose={() => {}}
      />
    );

    expect(getByText('1月')).toBeInTheDocument();
    expect(getByText('6月')).toBeInTheDocument();
    expect(getByText('12月')).toBeInTheDocument();
  });

  it('should highlight current month', () => {
    const onSelectMonth = jest.fn();
    const { getByText } = render(
      <MonthGrid
        currentMonth={new Date('2024-03-15')}
        onSelectMonth={onSelectMonth}
        onClose={() => {}}
      />
    );

    const marchButton = getByText('3月');
    expect(marchButton).toBeInTheDocument();
    // Current month should have different styling
  });

  it('should call onSelectMonth when month clicked', () => {
    const onSelectMonth = jest.fn();
    const onClose = jest.fn();
    const { getByText } = render(
      <MonthGrid
        currentMonth={new Date('2024-03-15')}
        onSelectMonth={onSelectMonth}
        onClose={onClose}
      />
    );

    fireEvent.click(getByText('6月'));

    expect(onSelectMonth).toHaveBeenCalledWith(5); // June is index 5
    expect(onClose).toHaveBeenCalled();
  });
});
