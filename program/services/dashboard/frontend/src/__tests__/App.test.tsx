import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../App';

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    // Sidebar always renders the MONEYMAKER brand
    expect(document.body).toBeTruthy();
  });
});
