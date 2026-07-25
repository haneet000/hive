import React, { useState, useEffect } from 'react';

const API_BASE = '/api';

function formatRejectReason(reasonStr) {
  if (!reasonStr) return { category: 'UNKNOWN', badgeClass: 'badge-orphan', detail: '' };

  if (reasonStr.startsWith('DUPLICATE_ORDER_ID_SUPERSEDED')) {
    const detail = reasonStr.replace('DUPLICATE_ORDER_ID_SUPERSEDED:', '').trim();
    return {
      category: 'DUPLICATE SUPERSEDED',
      badgeClass: 'badge-duplicate',
      detail: detail ? `Audit note: ${detail}` : 'Superseded by later order timestamp'
    };
  }

  if (reasonStr.startsWith('ORPHANED_CUSTOMER_ID')) {
    const detail = reasonStr.replace('ORPHANED_CUSTOMER_ID:', '').trim();
    return {
      category: 'ORPHANED CUSTOMER ID',
      badgeClass: 'badge-orphan',
      detail: detail ? `Quarantine note: ${detail}` : 'Referenced customer missing from feed'
    };
  }

  return {
    category: 'VALIDATION WARNING',
    badgeClass: 'badge-orphan',
    detail: reasonStr
  };
}

export default function App() {
  const [activeTab, setActiveTab] = useState('revenue');

  // Overview Stats state
  const [repeatRate, setRepeatRate] = useState(null);

  // Revenue state
  const [granularity, setGranularity] = useState('day');
  const [includeRefunds, setIncludeRefunds] = useState(false);
  const [revenueData, setRevenueData] = useState(null);
  const [loadingRevenue, setLoadingRevenue] = useState(false);

  // Top Customers state
  const [topBy, setTopBy] = useState('spend');
  const [topCustomers, setTopCustomers] = useState(null);
  const [loadingTop, setLoadingTop] = useState(false);

  // City AOV state
  const [cityAov, setCityAov] = useState(null);
  const [loadingCity, setLoadingCity] = useState(false);

  // Customer Orders lookup state
  const [searchCustId, setSearchCustId] = useState('CUST-0104');
  const [customerOrders, setCustomerOrders] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [loadingCust, setLoadingCust] = useState(false);

  // Ingestion Rejects state & Filter
  const [rejects, setRejects] = useState([]);
  const [rejectFilter, setRejectFilter] = useState('all');
  const [loadingRejects, setLoadingRejects] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/stats/repeat-purchase-rate`)
      .then(res => res.json())
      .then(data => setRepeatRate(data))
      .catch(err => console.error(err));
  }, []);

  // Fetch revenue
  useEffect(() => {
    if (activeTab === 'revenue') {
      setLoadingRevenue(true);
      fetch(`${API_BASE}/revenue?granularity=${granularity}&include_refunds=${includeRefunds}`)
        .then(res => res.json())
        .then(data => setRevenueData(data))
        .catch(err => console.error(err))
        .finally(() => setLoadingRevenue(false));
    }
  }, [activeTab, granularity, includeRefunds]);

  // Fetch Top Customers
  useEffect(() => {
    if (activeTab === 'top') {
      setLoadingTop(true);
      fetch(`${API_BASE}/customers/top?by=${topBy}&limit=20`)
        .then(res => res.json())
        .then(data => setTopCustomers(data))
        .catch(err => console.error(err))
        .finally(() => setLoadingTop(false));
    }
  }, [activeTab, topBy]);

  // Fetch City AOV
  useEffect(() => {
    if (activeTab === 'city') {
      setLoadingCity(true);
      fetch(`${API_BASE}/stats/aov-by-city`)
        .then(res => res.json())
        .then(data => setCityAov(data))
        .catch(err => console.error(err))
        .finally(() => setLoadingCity(false));
    }
  }, [activeTab]);

  // Fetch Customer Order Lookup
  const handleCustomerLookup = (e) => {
    if (e) e.preventDefault();
    if (!searchCustId) return;
    setLoadingCust(true);
    setSearchError(null);
    fetch(`${API_BASE}/customers/${searchCustId}/orders`)
      .then(res => {
        if (!res.ok) {
          throw new Error(`Customer '${searchCustId}' not found (Status 404)`);
        }
        return res.json();
      })
      .then(data => setCustomerOrders(data))
      .catch(err => {
        setCustomerOrders(null);
        setSearchError(err.message);
      })
      .finally(() => setLoadingCust(false));
  };

  useEffect(() => {
    if (activeTab === 'customer' && !customerOrders && !searchError) {
      handleCustomerLookup();
    }
  }, [activeTab]);

  // Fetch Rejects
  useEffect(() => {
    if (activeTab === 'rejects') {
      setLoadingRejects(true);
      fetch(`${API_BASE}/ingestion/rejects?limit=100`)
        .then(res => res.json())
        .then(data => setRejects(data))
        .catch(err => console.error(err))
        .finally(() => setLoadingRejects(false));
    }
  }, [activeTab]);

  // Filtered rejects
  const filteredRejects = rejects.filter(r => {
    if (rejectFilter === 'duplicates') return r.reason.startsWith('DUPLICATE_ORDER_ID_SUPERSEDED');
    if (rejectFilter === 'orphans') return r.reason.startsWith('ORPHANED_CUSTOMER_ID');
    return true;
  });

  const duplicateCount = rejects.filter(r => r.reason.startsWith('DUPLICATE_ORDER_ID_SUPERSEDED')).length;
  const orphanCount = rejects.filter(r => r.reason.startsWith('ORPHANED_CUSTOMER_ID')).length;

  return (
    <div className="dashboard-container">
      {/* Fixed Header */}
      <header>
        <div>
          <h1>Hive E-Commerce Analytics</h1>
          <p>Live Third-Party Feed Cleaning & Analytics Dashboard</p>
        </div>
        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'revenue' ? 'active' : ''}`}
            onClick={() => setActiveTab('revenue')}
          >
            Revenue
          </button>
          <button
            className={`nav-tab ${activeTab === 'top' ? 'active' : ''}`}
            onClick={() => setActiveTab('top')}
          >
            Top Customers
          </button>
          <button
            className={`nav-tab ${activeTab === 'city' ? 'active' : ''}`}
            onClick={() => setActiveTab('city')}
          >
            City AOV
          </button>
          <button
            className={`nav-tab ${activeTab === 'customer' ? 'active' : ''}`}
            onClick={() => setActiveTab('customer')}
          >
            Customer Lookup
          </button>
          <button
            className={`nav-tab ${activeTab === 'rejects' ? 'active' : ''}`}
            onClick={() => setActiveTab('rejects')}
          >
            Data Audit
          </button>
        </nav>
      </header>

      {/* Global Stat KPI Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Total Gross Revenue</div>
          <div className="value" style={{ color: 'var(--accent-emerald)' }}>
            ₹{revenueData?.total_revenue?.toLocaleString('en-IN') || '—'}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Repeat Purchase Rate</div>
          <div className="value" style={{ color: 'var(--accent-blue)' }}>
            {repeatRate ? `${repeatRate.repeat_purchase_rate_pct}%` : '—'}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Repeat Customers</div>
          <div className="value" style={{ color: 'var(--accent-purple)' }}>
            {repeatRate ? `${repeatRate.repeat_customers_count} / ${repeatRate.total_customers_with_orders}` : '—'}
          </div>
        </div>
      </div>

      {/* TAB 1: REVENUE */}
      {activeTab === 'revenue' && (
        <div className="main-card">
          <div className="card-header">
            <div className="card-title">Revenue Over Time</div>
            <div className="controls">
              <label>
                Granularity:
                <select value={granularity} onChange={(e) => setGranularity(e.target.value)}>
                  <option value="day">Daily</option>
                  <option value="week">Weekly</option>
                </select>
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={includeRefunds}
                  onChange={(e) => setIncludeRefunds(e.target.checked)}
                />
                Net Refunds
              </label>
            </div>
          </div>

          <div className="table-scroll-container">
            {loadingRevenue ? (
              <div className="loading">Loading revenue data...</div>
            ) : revenueData && revenueData.data.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Orders Count</th>
                    <th>Total Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {revenueData.data.map((dp, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{dp.period}</td>
                      <td>{dp.order_count}</td>
                      <td style={{ color: dp.revenue < 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)', fontWeight: 600 }}>
                        ₹{dp.revenue.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty">No revenue data available.</div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: TOP CUSTOMERS */}
      {activeTab === 'top' && (
        <div className="main-card">
          <div className="card-header">
            <div className="card-title">Top Customers</div>
            <div className="controls">
              <label>
                Sort By:
                <select value={topBy} onChange={(e) => setTopBy(e.target.value)}>
                  <option value="spend">Total Spend</option>
                  <option value="orders">Completed Orders Count</option>
                </select>
              </label>
            </div>
          </div>

          <div className="table-scroll-container">
            {loadingTop ? (
              <div className="loading">Loading top customers...</div>
            ) : topCustomers && topCustomers.data.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Customer ID</th>
                    <th>Name</th>
                    <th>City</th>
                    <th>Email</th>
                    <th>Completed Orders</th>
                    <th>Total Spend</th>
                  </tr>
                </thead>
                <tbody>
                  {topCustomers.data.map((c) => (
                    <tr key={c.customer_id}>
                      <td>
                        <code>{c.customer_id}</code>
                      </td>
                      <td style={{ fontWeight: 600 }}>{c.name}</td>
                      <td>{c.city}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{c.email || '—'}</td>
                      <td>{c.order_count}</td>
                      <td style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>
                        ₹{c.total_spend.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty">No customers found.</div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: CITY AOV */}
      {activeTab === 'city' && (
        <div className="main-card">
          <div className="card-header">
            <div className="card-title">Average Order Value (AOV) by City</div>
          </div>

          <div className="table-scroll-container">
            {loadingCity ? (
              <div className="loading">Loading city AOV data...</div>
            ) : cityAov && cityAov.data.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>City</th>
                    <th>Total Completed Orders</th>
                    <th>Total Revenue</th>
                    <th>Average Order Value (AOV)</th>
                  </tr>
                </thead>
                <tbody>
                  {cityAov.data.map((item) => (
                    <tr key={item.city}>
                      <td style={{ fontWeight: 600 }}>{item.city}</td>
                      <td>{item.total_orders}</td>
                      <td>₹{item.total_revenue.toLocaleString('en-IN')}</td>
                      <td style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
                        ₹{item.aov.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty">No city data available.</div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: CUSTOMER LOOKUP */}
      {activeTab === 'customer' && (
        <div className="main-card">
          <div className="card-header">
            <div className="card-title">Customer Order Lookup</div>
            <form onSubmit={handleCustomerLookup} className="controls">
              <label>
                Customer ID:
                <input
                  type="text"
                  value={searchCustId}
                  onChange={(e) => setSearchCustId(e.target.value)}
                  placeholder="e.g. CUST-0104"
                />
              </label>
              <button type="submit" className="btn-primary">
                Search
              </button>
            </form>
          </div>

          <div className="table-scroll-container custom-scroll" style={{ padding: '1rem', background: 'transparent' }}>
            {loadingCust && <div className="loading">Searching customer history...</div>}

            {searchError && (
              <div className="empty" style={{ color: 'var(--accent-rose)' }}>
                ⚠️ {searchError}
              </div>
            )}

            {customerOrders && (
              <div>
                <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '1rem 1.25rem', borderRadius: '10px', marginBottom: '1.25rem', border: '1px solid var(--border)' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '0.4rem', color: '#fff' }}>{customerOrders.customer.name}</h3>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                    <span>📍 City: <strong style={{ color: '#fff' }}>{customerOrders.customer.city}</strong></span>
                    <span>📧 Email: <strong style={{ color: '#fff' }}>{customerOrders.customer.email || 'None'}</strong></span>
                    <span>📅 Member Since: <strong style={{ color: '#fff' }}>{customerOrders.customer.signup_date}</strong></span>
                  </div>
                </div>

                <h4 style={{ marginBottom: '1rem', fontSize: '0.95rem', color: 'var(--text-muted)' }}>
                  Order History ({customerOrders.total} {customerOrders.total === 1 ? 'order' : 'orders'})
                </h4>

                {customerOrders.orders.length > 0 ? (
                  customerOrders.orders.map((ord) => (
                    <div
                      key={ord.id}
                      style={{
                        border: '1px solid var(--border)',
                        borderRadius: '10px',
                        padding: '1rem',
                        marginBottom: '1rem',
                        background: 'rgba(15, 23, 42, 0.6)'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div>
                          <code>{ord.id}</code>
                          <span style={{ marginLeft: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                            {new Date(ord.order_date).toLocaleString()}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <span className={`badge badge-${ord.status}`}>{ord.status}</span>
                          <span style={{ fontWeight: 700, fontSize: '1.05rem', color: ord.total_amount < 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}>
                            ₹{ord.total_amount.toLocaleString('en-IN')}
                          </span>
                        </div>
                      </div>

                      {ord.items && ord.items.length > 0 && (
                        <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.5rem' }}>
                          <div style={{ color: 'var(--text-muted)', marginBottom: '0.35rem', fontWeight: 600 }}>Purchased Items:</div>
                          <ul style={{ listStyleType: 'none', paddingLeft: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                            {ord.items.map((item, i) => (
                              <li key={i} style={{ display: 'flex', justifyContent: 'space-between', background: 'rgba(255,255,255,0.02)', padding: '0.4rem 0.75rem', borderRadius: '6px' }}>
                                <span>{item.name} <code style={{ fontSize: '0.75rem' }}>{item.sku}</code></span>
                                <span style={{ color: 'var(--text-muted)' }}>
                                  Qty: {item.qty} × ₹{item.unit_price} = <strong style={{ color: '#fff' }}>₹{(item.qty * item.unit_price).toLocaleString('en-IN')}</strong>
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="empty">No order history recorded for this customer.</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: INGESTION REJECTS AUDIT */}
      {activeTab === 'rejects' && (
        <div className="main-card">
          <div className="card-header">
            <div className="card-title">Ingestion Validation Audit Log</div>
            <div className="controls">
              <button
                className={`filter-btn ${rejectFilter === 'all' ? 'active' : ''}`}
                onClick={() => setRejectFilter('all')}
              >
                All Audit Rejects ({rejects.length})
              </button>
              <button
                className={`filter-btn ${rejectFilter === 'duplicates' ? 'active' : ''}`}
                onClick={() => setRejectFilter('duplicates')}
              >
                Duplicates ({duplicateCount})
              </button>
              <button
                className={`filter-btn ${rejectFilter === 'orphans' ? 'active' : ''}`}
                onClick={() => setRejectFilter('orphans')}
              >
                Orphaned Customer IDs ({orphanCount})
              </button>
            </div>
          </div>

          <div className="table-scroll-container">
            {loadingRejects ? (
              <div className="loading">Loading audit logs...</div>
            ) : filteredRejects.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th style={{ width: '60px' }}>ID</th>
                    <th style={{ width: '90px' }}>Entity</th>
                    <th style={{ width: '130px' }}>Entity ID</th>
                    <th>Validation & Quarantine Reason</th>
                    <th style={{ width: '170px' }}>Log Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRejects.map((r) => {
                    const parsed = formatRejectReason(r.reason);
                    return (
                      <tr key={r.id}>
                        <td><span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>#{r.id}</span></td>
                        <td>
                          <span className="badge badge-entity">{r.entity_type}</span>
                        </td>
                        <td>
                          <code>{r.entity_id || '—'}</code>
                        </td>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <div>
                              <span className={`badge ${parsed.badgeClass}`}>
                                {parsed.category}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              {parsed.detail}
                            </div>
                          </div>
                        </td>
                        <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                          {new Date(r.created_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div className="empty">No rejection records match the selected filter.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
