import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import DataTable from '../../components/common/DataTable';

interface TestRow {
  name: string;
  value: number;
}

const columns = [
  { key: 'name', header: 'Name' },
  { key: 'value', header: 'Value' },
];

describe('DataTable', () => {
  it('renders empty message when no data', () => {
    render(<DataTable<TestRow> columns={columns} data={[]} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('renders custom empty message', () => {
    render(<DataTable<TestRow> columns={columns} data={[]} emptyMessage="Nothing here" />);
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('renders headers and rows', () => {
    const data: TestRow[] = [
      { name: 'EURUSD', value: 100 },
      { name: 'GBPUSD', value: 200 },
    ];
    render(<DataTable<TestRow> columns={columns} data={data} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Value')).toBeInTheDocument();
    expect(screen.getByText('EURUSD')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
  });

  it('uses custom render function', () => {
    const customColumns = [
      { key: 'name', header: 'Name' },
      { key: 'value', header: 'Value', render: (row: TestRow) => `$${row.value}` },
    ];
    render(<DataTable<TestRow> columns={customColumns} data={[{ name: 'X', value: 42 }]} />);
    expect(screen.getByText('$42')).toBeInTheDocument();
  });

  it('shows dash for null/undefined values', () => {
    const data = [{ name: 'Test', value: undefined as any }];
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getByText('-')).toBeInTheDocument();
  });
});
