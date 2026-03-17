// ─── Tests for js/ui.js helpers ──────────────────────────
// Tests pure utility functions. DOM-dependent functions (updateCard, fetchAll)
// require a full browser environment and are tested via manual integration testing.

describe('gradientColor', () => {
  it('returns a red-ish color for t=0 when higherIsGood=true (worst)', () => {
    const color = gradientColor(0, true);
    assert.ok(color.startsWith('rgba('), 'should return rgba string');
    assert.ok(color.includes(',40,60,'), 'should be in red range');
  });

  it('returns a green-ish color for t=1 when higherIsGood=true (best)', () => {
    const color = gradientColor(1, true);
    assert.ok(color.startsWith('rgba(0,'), 'should start with 0 red channel for green');
  });

  it('inverts scale when higherIsGood=false', () => {
    const goodHigh  = gradientColor(1, true);
    const badHigh   = gradientColor(1, false);
    const goodLow   = gradientColor(0, true);
    const badLow    = gradientColor(0, false);
    // When higherIsGood=false, t=1 (high) should be red; t=0 (low) should be green
    assert.equal(goodHigh, badLow,  'high-when-good = low-when-bad');
    assert.equal(goodLow,  badHigh, 'low-when-good = high-when-bad');
  });

  it('returns mid-range color for t=0.5', () => {
    const color = gradientColor(0.5, true);
    assert.ok(color.startsWith('rgba('), 'should return rgba string');
  });
});

describe('cellColor', () => {
  // Mock HIGHER_IS_GOOD (normally defined per-page)
  before(() => { window._HIGHER_IS_GOOD_BAK = window.HIGHER_IS_GOOD; window.HIGHER_IS_GOOD = ['GDP']; });
  after(()  => { window.HIGHER_IS_GOOD = window._HIGHER_IS_GOOD_BAK; });

  it('returns green for positive Spread value', () => {
    assert.equal(cellColor(0.5, 'Spread', false), 'rgba(0,190,90,0.38)');
  });

  it('returns red for negative Spread value', () => {
    assert.equal(cellColor(-0.5, 'Spread', false), 'rgba(220,40,60,0.38)');
  });

  it('returns green for positive change when higherIsGood (isChange=true, GDP)', () => {
    assert.equal(cellColor(1, 'GDP', true), 'rgba(0,190,90,0.38)');
  });

  it('returns red for negative change when higherIsGood (isChange=true, GDP)', () => {
    assert.equal(cellColor(-1, 'GDP', true), 'rgba(220,40,60,0.38)');
  });

  it('returns red for positive change when !higherIsGood (isChange=true, CPI)', () => {
    assert.equal(cellColor(1, 'CPI', true), 'rgba(220,40,60,0.38)');
  });

  it('returns green for negative change when !higherIsGood (isChange=true, CPI)', () => {
    assert.equal(cellColor(-1, 'CPI', true), 'rgba(0,190,90,0.38)');
  });

  it('returns null for non-change, non-Spread values', () => {
    assert.equal(cellColor(5, 'CPI', false), null);
  });
});
