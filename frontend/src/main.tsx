
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  BrowserRouter,
  NavLink,
  useLocation,
} from 'react-router-dom';
import {
  useQuery,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query';
import {
  PieChart,
  Pie,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  Activity,
  Files,
  ClipboardList,
  CheckCircle2,
  Workflow,
  ShieldCheck,
  LayoutDashboard,
  LogOut,
} from 'lucide-react';

import './style.css';

// --------------------------------------------------
// API CONFIGURATION
// --------------------------------------------------

const BASE = import.meta.env.VITE_API_URL || '';

const qc = new QueryClient();

async function api(
  path: string,
  opts: RequestInit = {}
) {
  const response = await fetch(
    BASE + '/api/v1' + path,
    {
      ...opts,
      headers: {
        ...(opts.body instanceof FormData
          ? {}
          : { 'Content-Type': 'application/json' }),
        Authorization:
          'Bearer ' + localStorage.getItem('token'),
        ...opts.headers,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      (await response.text()).slice(0, 250)
    );
  }

  return response.json();
}

// --------------------------------------------------
// LOGIN
// --------------------------------------------------

function Login() {
  const [user, setUser] = useState('admin');
  const [pass, setPass] = useState('DemoPass123!');
  const [error, setError] = useState('');

  async function handleLogin(
    e: React.FormEvent<HTMLFormElement>
  ) {
    e.preventDefault();
    setError('');

    try {
      const result = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          username: user,
          password: pass,
        }),
      });

      localStorage.setItem(
        'token',
        result.access_token
      );

      window.location.href = '/';
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <main className="login">
      <form onSubmit={handleLogin}>
        <h1>
          CareFlow <em>AI</em>
        </h1>

        <p>
          Healthcare workflow intelligence ·
          Synthetic demo only
        </p>

        <label>
          Username
          <input
            value={user}
            onChange={(e) =>
              setUser(e.target.value)
            }
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={pass}
            onChange={(e) =>
              setPass(e.target.value)
            }
          />
        </label>

        <button type="submit">
          Sign in
        </button>

        {error && (
          <p className="error">{error}</p>
        )}
      </form>
    </main>
  );
}

// --------------------------------------------------
// DATA FETCHING
// --------------------------------------------------

function Data({
  path,
  children,
}: {
  path: string;
  children: (data: any) => React.ReactNode;
}) {
  const query = useQuery({
    queryKey: [path],
    queryFn: () => api(path),
  });

  if (query.isLoading) {
    return <p>Loading...</p>;
  }

  if (query.error) {
    return (
      <p className="error">
        {String(query.error)}
      </p>
    );
  }

  return <>{children(query.data)}</>;
}

// --------------------------------------------------
// SIDEBAR NAVIGATION
// --------------------------------------------------

const nav = [
  ['/', 'Dashboard', LayoutDashboard],
  ['/documents', 'Documents', Files],
  ['/referrals', 'Referrals', ClipboardList],
  ['/reviews', 'Review Queue', ShieldCheck],
  ['/tasks', 'Follow-Up Tasks', CheckCircle2],
  ['/integrations', 'Integrations', Workflow],
  ['/audit', 'Audit Logs', Activity],
] as const;

// --------------------------------------------------
// MAIN LAYOUT
// --------------------------------------------------

function Shell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="shell">
      <aside>
        <h2>
          ✚ CareFlow <em>AI</em>
        </h2>

        <small>WORKSPACE</small>

        {nav.map(([url, label, Icon]) => (
          <NavLink
            key={url}
            to={url}
            end={url === '/'}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}

        <button
          className="logout"
          onClick={() => {
            localStorage.removeItem('token');
            window.location.href = '/';
          }}
        >
          <LogOut size={16} />
          Sign out
        </button>
      </aside>

      <main>
        <header>
          <span>
            CareFlow AI / Administrative workspace
          </span>

          <span className="pill">
            ● Demo environment
          </span>
        </header>

        {children}
      </main>
    </div>
  );
}

// --------------------------------------------------
// PAGE HEADING
// --------------------------------------------------

function Head({
  title,
  desc,
}: {
  title: string;
  desc: string;
}) {
  return (
    <div className="heading">
      <h1>{title}</h1>
      <p>{desc}</p>
    </div>
  );
}

// --------------------------------------------------
// REUSABLE TABLE
// --------------------------------------------------

function Table({
  rows,
  cols,
}: {
  rows: any[];
  cols: string[];
}) {
  if (!rows.length) {
    return (
      <p className="empty">
        No records yet.
      </p>
    );
  }

  return (
    <div className="tablewrap">
      <table>
        <thead>
          <tr>
            {cols.map((col) => (
              <th key={col}>
                {col.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, index) => (
            <tr key={row.id || index}>
              {cols.map((col) => (
                <td key={col}>
                  {col === 'created_at'
                    ? row[col]
                      ? new Date(
                          row[col]
                        ).toLocaleString()
                      : '—'
                    : String(row[col] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --------------------------------------------------
// DASHBOARD
// --------------------------------------------------

function Dashboard() {
  return (
    <>
      <Head
        title="Overview"
        desc="Real-time operational metrics from the CareFlow API"
      />

      <Data path="/dashboard/overview">
        {(data) => (
          <>
            <div className="stats">
              {[
                [
                  'Total referrals',
                  data.total_referrals,
                ],
                [
                  'Awaiting documents',
                  data.awaiting_documents,
                ],
                [
                  'Pending signatures',
                  data.pending_signatures,
                ],
                [
                  'Documents processed',
                  data.documents_processed,
                ],
                [
                  'Needs review',
                  data.needs_review,
                ],
                [
                  'Follow-up tasks',
                  data.pending_tasks,
                ],
              ].map(([label, value]) => (
                <section
                  className="stat"
                  key={String(label)}
                >
                  <span>{label}</span>
                  <strong>{value}</strong>
                </section>
              ))}
            </div>

            <div className="two">
              <section className="panel">
                <h3>Referral status</h3>

                <ResponsiveContainer
                  width="100%"
                  height={260}
                >
                  <PieChart>
                    <Pie
                      data={data.referral_statuses.filter(
                        (item: any) =>
                          item.value
                      )}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={92}
                      label
                    >
                      {data.referral_statuses.map(
                        (_: any, index: number) => (
                          <Cell
                            key={index}
                            fill={
                              [
                                '#0f766e',
                                '#0891b2',
                                '#2563eb',
                                '#f59e0b',
                                '#7c3aed',
                                '#16a34a',
                                '#64748b',
                              ][index % 7]
                            }
                          />
                        )
                      )}
                    </Pie>

                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </section>

              <section className="panel">
                <h3>Document distribution</h3>

                {data.document_types
                  .filter(
                    (item: any) => item.value
                  )
                  .map((item: any) => (
                    <p
                      className="barrow"
                      key={item.name}
                    >
                      <span>{item.name}</span>
                      <b>{item.value}</b>
                    </p>
                  ))}

                {!data.document_types.some(
                  (item: any) => item.value
                ) && (
                  <p>
                    No documents yet.
                    Upload one to begin.
                  </p>
                )}
              </section>
            </div>
          </>
        )}
      </Data>

      <section className="panel">
        <h3>Recent activity</h3>

        <Data path="/dashboard/activity">
          {(data) => (
            <Table
              rows={data.items}
              cols={[
                'action',
                'entity_type',
                'created_at',
              ]}
            />
          )}
        </Data>
      </section>
    </>
  );
}

// --------------------------------------------------
// REFERRALS
// --------------------------------------------------

function Referrals() {
  const [name, setName] = useState('');
  const [service, setService] = useState('ABA');
  const [error, setError] = useState('');

  async function createReferral(
    e: React.FormEvent<HTMLFormElement>
  ) {
    e.preventDefault();
    setError('');

    try {
      await api('/referrals', {
        method: 'POST',
        body: JSON.stringify({
          patient_name: name,
          requested_service: service,
        }),
      });

      setName('');

      await qc.invalidateQueries({
        queryKey: ['/referrals'],
      });
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <>
      <Head
        title="Referrals"
        desc="Manage intake and completeness checks"
      />

      <section className="panel">
        <h3>Create referral</h3>

        <form
          className="inline"
          onSubmit={createReferral}
        >
          <input
            required
            placeholder="Synthetic patient name"
            value={name}
            onChange={(e) =>
              setName(e.target.value)
            }
          />

          <select
            value={service}
            onChange={(e) =>
              setService(e.target.value)
            }
          >
            <option>ABA</option>
            <option>Speech Therapy</option>
          </select>

          <button type="submit">
            Create referral
          </button>
        </form>

        {error && (
          <p className="error">{error}</p>
        )}
      </section>

      <section className="panel">
        <h3>Referral records</h3>

        <Data path="/referrals">
          {(data) => (
            <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>Patient</th>
                    <th>Service</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {data.items.map(
                    (referral: any) => (
                      <tr key={referral.id}>
                        <td>
                          {referral.patient_name}
                        </td>

                        <td>
                          {referral.requested_service}
                        </td>

                        <td>
                          <span className="tag">
                            {referral.status}
                          </span>
                        </td>

                        <td>
                          <button
                            className="secondary"
                            onClick={async () => {
                              try {
                                await api(
                                  '/referrals/' +
                                    referral.id +
                                    '/validate',
                                  { method: 'POST' }
                                );

                                await qc.invalidateQueries();
                              } catch (err) {
                                alert(String(err));
                              }
                            }}
                          >
                            Validate
                          </button>
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Data>
      </section>
    </>
  );
}

// --------------------------------------------------
// DOCUMENTS
// --------------------------------------------------

function Documents() {
  const [files, setFiles] =
    useState<FileList | null>(null);

  const [referralId, setReferralId] =
    useState('');

  const [message, setMessage] =
    useState('');

  async function uploadDocuments(
    e: React.FormEvent<HTMLFormElement>
  ) {
    e.preventDefault();

    if (!files || files.length === 0) {
      setMessage('Please select a file.');
      return;
    }

    const formData = new FormData();

    Array.from(files).forEach((file) => {
      formData.append('files', file);
    });

    try {
      await api(
        '/documents/upload' +
          (referralId
            ? '?referral_id=' +
              encodeURIComponent(referralId)
            : ''),
        {
          method: 'POST',
          body: formData,
        }
      );

      setMessage('Uploaded successfully.');

      await qc.invalidateQueries();
    } catch (err) {
      setMessage(String(err));
    }
  }

  async function previewDocument(id: string) {
    try {
      const response = await fetch(
        BASE +
          '/api/v1/documents/' +
          id +
          '/file',
        {
          headers: {
            Authorization:
              'Bearer ' +
              localStorage.getItem('token'),
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          'Unable to open document'
        );
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      window.open(url, '_blank');

      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 60000);
    } catch (err) {
      alert(String(err));
    }
  }

  return (
    <>
      <Head
        title="Documents"
        desc="Secure uploads, extraction, and human verification"
      />

      <section className="panel">
        <h3>Upload documents</h3>

        <form
          className="inline"
          onSubmit={uploadDocuments}
        >
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            multiple
            onChange={(e) =>
              setFiles(e.target.files)
            }
          />

          <select
            value={referralId}
            onChange={(e) =>
              setReferralId(e.target.value)
            }
          >
            <option value="">
              Unlinked
            </option>

            <ReferralOptions />
          </select>

          <button type="submit">
            Upload
          </button>
        </form>

        {message && <p>{message}</p>}
      </section>

      <section className="panel">
        <h3>Document library</h3>

        <Data path="/documents">
          {(data) => (
            <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {data.items.map(
                    (document: any) => (
                      <tr key={document.id}>
                        <td>
                          {document.filename}
                        </td>

                        <td>
                          {document.document_type}
                        </td>

                        <td>
                          <span className="tag">
                            {document.status}
                          </span>
                        </td>

                        <td>
                          <button
                            className="secondary"
                            onClick={async () => {
                              try {
                                await api(
                                  '/documents/' +
                                    document.id +
                                    '/process',
                                  { method: 'POST' }
                                );

                                await qc.invalidateQueries();
                              } catch (err) {
                                alert(String(err));
                              }
                            }}
                          >
                            Process / Retry
                          </button>

                          {' '}

                          <button
                            className="secondary"
                            onClick={() =>
                              previewDocument(
                                document.id
                              )
                            }
                          >
                            Preview
                          </button>
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Data>
      </section>
    </>
  );
}

// --------------------------------------------------
// REFERRAL OPTIONS
// --------------------------------------------------

function ReferralOptions() {
  return (
    <Data path="/referrals">
      {(data) =>
        data.items.map((referral: any) => (
          <option
            key={referral.id}
            value={referral.id}
          >
            {referral.patient_name}
          </option>
        ))
      }
    </Data>
  );
}

// --------------------------------------------------
// REVIEWS
// --------------------------------------------------

function Reviews() {
  return (
    <>
      <Head
        title="Human review queue"
        desc="Review uncertain AI results before approval"
      />

      <Data path="/reviews">
        {(data) => (
          <section className="panel">
            <Table
              rows={data.items}
              cols={[
                'filename',
                'status',
                'notes',
              ]}
            />

            {data.items
              .filter(
                (review: any) =>
                  review.status === 'Pending'
              )
              .map((review: any) => (
                <div
                  className="review"
                  key={review.id}
                >
                  <strong>
                    {review.filename}
                  </strong>

                  <button
                    onClick={async () => {
                      const notes =
                        prompt('Approval notes') ||
                        '';

                      try {
                        await api(
                          '/reviews/' +
                            review.id +
                            '/approve',
                          {
                            method: 'POST',
                            body: JSON.stringify({
                              notes,
                            }),
                          }
                        );

                        await qc.invalidateQueries();
                      } catch (err) {
                        alert(String(err));
                      }
                    }}
                  >
                    Approve
                  </button>

                  <button
                    className="secondary"
                    onClick={async () => {
                      const notes =
                        prompt(
                          'Reason for rejection'
                        ) || '';

                      try {
                        await api(
                          '/reviews/' +
                            review.id +
                            '/reject',
                          {
                            method: 'POST',
                            body: JSON.stringify({
                              notes,
                            }),
                          }
                        );

                        await qc.invalidateQueries();
                      } catch (err) {
                        alert(String(err));
                      }
                    }}
                  >
                    Reject
                  </button>
                </div>
              ))}
          </section>
        )}
      </Data>
    </>
  );
}

// --------------------------------------------------
// TASKS
// --------------------------------------------------

function Tasks() {
  return (
    <>
      <Head
        title="Follow-up tasks"
        desc="Administrative tasks generated by validation workflows"
      />

      <Data path="/tasks">
        {(data) => (
          <section className="panel">
            {data.items.length ? (
              data.items.map((task: any) => (
                <div
                  className="task"
                  key={task.id}
                >
                  <div>
                    <strong>
                      {task.title}
                    </strong>

                    <p>{task.message}</p>
                  </div>

                  <select
                    value={task.status}
                    onChange={async (e) => {
                      try {
                        await api(
                          '/tasks/' + task.id,
                          {
                            method: 'PATCH',
                            body: JSON.stringify({
                              status:
                                e.target.value,
                            }),
                          }
                        );

                        await qc.invalidateQueries();
                      } catch (err) {
                        alert(String(err));
                      }
                    }}
                  >
                    {[
                      'Pending',
                      'In Progress',
                      'Waiting',
                      'Completed',
                      'Cancelled',
                    ].map((status) => (
                      <option key={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                </div>
              ))
            ) : (
              <p>No follow-up tasks.</p>
            )}
          </section>
        )}
      </Data>
    </>
  );
}

// --------------------------------------------------
// INTEGRATIONS
// --------------------------------------------------

function Integrations() {
  return (
    <>
      <Head
        title="Integrations"
        desc="Safe mock CRM, task, and email adapters"
      />

      <Data path="/integrations">
        {(data) => (
          <div className="cards">
            {data.items.map(
              (integration: any) => (
                <section
                  className="panel"
                  key={integration.id}
                >
                  <h3>
                    {integration.name}
                  </h3>

                  <p>
                    Mode: {integration.mode}
                  </p>

                  <button
                    onClick={async () => {
                      try {
                        await api(
                          '/integrations/' +
                            integration.id +
                            '/sync',
                          { method: 'POST' }
                        );

                        await qc.invalidateQueries();
                      } catch (err) {
                        alert(String(err));
                      }
                    }}
                  >
                    Run mock sync
                  </button>
                </section>
              )
            )}
          </div>
        )}
      </Data>

      <section className="panel">
        <h3>Synchronization history</h3>

        <Data path="/integrations/logs">
          {(data) => (
            <Table
              rows={data.items}
              cols={[
                'provider',
                'status',
                'created_at',
              ]}
            />
          )}
        </Data>
      </section>
    </>
  );
}

// --------------------------------------------------
// AUDIT LOGS
// --------------------------------------------------

function Audit() {
  return (
    <>
      <Head
        title="Audit history"
        desc="Recorded administrative actions and processing events"
      />

      <section className="panel">
        <Data path="/audit-logs">
          {(data) => (
            <Table
              rows={data.items}
              cols={[
                'action',
                'entity_type',
                'entity_id',
                'created_at',
              ]}
            />
          )}
        </Data>
      </section>
    </>
  );
}

// --------------------------------------------------
// APP ROUTING - FIXED
// --------------------------------------------------

function App() {
  // useLocation triggers a React re-render
  // whenever the sidebar navigation changes.
  const location = useLocation();

  const path = location.pathname;

  if (!localStorage.getItem('token')) {
    return <Login />;
  }

  let page: React.ReactNode;

  switch (path) {
    case '/documents':
      page = <Documents />;
      break;

    case '/referrals':
      page = <Referrals />;
      break;

    case '/reviews':
      page = <Reviews />;
      break;

    case '/tasks':
      page = <Tasks />;
      break;

    case '/integrations':
      page = <Integrations />;
      break;

    case '/audit':
      page = <Audit />;
      break;

    default:
      page = <Dashboard />;
      break;
  }

  return <Shell>{page}</Shell>;
}

// --------------------------------------------------
// APPLICATION ENTRY POINT
// --------------------------------------------------

createRoot(
  document.getElementById('root')!
).render(
  <QueryClientProvider client={qc}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>
);
