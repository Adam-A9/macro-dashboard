// ─── Tests for js/api.js utilities ───────────────────────
// These test pure functions that have no DOM or network dependencies.

describe('parseFREDJson', () => {
  it('returns observations in chronological order (reversed)', () => {
    const json = {
      observations: [
        { date: '2024-03-01', value: '3.5' },
        { date: '2024-02-01', value: '3.4' },
        { date: '2024-01-01', value: '3.2' },
      ]
    };
    const result = parseFREDJson(json);
    assert.equal(result.length, 3);
    assert.equal(result[0].date, '2024-01-01');
    assert.equal(result[2].date, '2024-03-01');
  });

  it('filters out missing values (dots and empty strings)', () => {
    const json = {
      observations: [
        { date: '2024-03-01', value: '3.5' },
        { date: '2024-02-01', value: '.'   },
        { date: '2024-01-01', value: ''    },
      ]
    };
    const result = parseFREDJson(json);
    assert.equal(result.length, 1);
    assert.equal(result[0].value, 3.5);
  });

  it('parses values as floats', () => {
    const json = { observations: [{ date: '2024-01-01', value: '123.456' }] };
    const result = parseFREDJson(json);
    assert.equal(typeof result[0].value, 'number');
    assert.equal(result[0].value, 123.456);
  });

  it('throws when observations key is missing', () => {
    assert.throws(() => parseFREDJson({}), /No observations/);
    assert.throws(() => parseFREDJson({ error: 'bad' }), /No observations/);
  });

  it('returns empty array when all values are missing', () => {
    const json = {
      observations: [
        { date: '2024-01-01', value: '.' },
        { date: '2024-02-01', value: '' },
      ]
    };
    assert.equal(parseFREDJson(json).length, 0);
  });
});

describe('filterToTwoYears', () => {
  it('filters observations older than two years', () => {
    const year = new Date().getFullYear();
    const obs = [
      { date: (year - 3) + '-06-01', value: 1 },
      { date: (year - 2) + '-01-01', value: 2 }, // exactly on cutoff — included
      { date: (year - 1) + '-06-01', value: 3 },
      { date: year       + '-01-01', value: 4 },
    ];
    const result = filterToTwoYears(obs);
    assert.equal(result.length, 3);
    assert.equal(result[0].value, 2);
  });

  it('returns all when everything is within two years', () => {
    const year = new Date().getFullYear();
    const obs = [
      { date: (year - 1) + '-01-01', value: 1 },
      { date:  year      + '-01-01', value: 2 },
    ];
    assert.equal(filterToTwoYears(obs).length, 2);
  });

  it('returns empty array for empty input', () => {
    assert.deepEqual(filterToTwoYears([]), []);
  });
});

describe('sleep', () => {
  it('resolves after approximately the specified delay', async () => {
    const start = Date.now();
    await sleep(50);
    const elapsed = Date.now() - start;
    assert.ok(elapsed >= 45, 'should wait at least ~50ms');
  });
});
