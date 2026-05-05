import { Fragment, useEffect, useState } from "react"
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  IconButton,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material"
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown"
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight"
import EditIcon from "@mui/icons-material/EditOutlined"
import DeleteIcon from "@mui/icons-material/DeleteOutlined"
import DescriptionIcon from "@mui/icons-material/DescriptionOutlined"
import ContentCopyIcon from "@mui/icons-material/ContentCopyOutlined"
import CheckIcon from "@mui/icons-material/Check"
import { api } from "../lib/api"
import { DocumentDetailsView } from "./DocumentDetailsView"
import type { Order, OrderCreate, OrderStatus, OrderedItem } from "../types/api"

const STATUSES: OrderStatus[] = [
  "pending",
  "processing",
  "completed",
  "cancelled",
]

interface Props {
  refreshKey: number
  onToast?: (msg: string, kind?: "success" | "error") => void
}

const statusColor = (
  s: OrderStatus,
): "warning" | "info" | "success" | "error" => {
  switch (s) {
    case "pending":
      return "warning"
    case "processing":
      return "info"
    case "completed":
      return "success"
    case "cancelled":
      return "error"
  }
}

const confidenceColor = (c: string | null): "success" | "warning" | "error" => {
  if (c === "high") return "success"
  if (c === "medium") return "warning"
  return "error"
}

function OriginCell({ order }: { order: Order }) {
  if (order.extraction_confidence) {
    return (
      <Stack direction="row" spacing={0.75} alignItems="center">
        <DescriptionIcon fontSize="small" color="primary" />
        <Chip
          label={order.extraction_confidence}
          size="small"
          color={confidenceColor(order.extraction_confidence)}
          variant="outlined"
        />
      </Stack>
    )
  }
  return <Chip label="Manual" size="small" variant="outlined" />
}

function describeItem(item: OrderedItem): string {
  const desc = (item.description || "").trim()
  const code = (item.code || "").trim()
  if (desc && code) return `${code} · ${desc}`
  return desc || code || "(unnamed item)"
}

function RawJsonCopyButton({
  data,
  onToast,
}: {
  data: unknown
  onToast?: (msg: string, kind?: "success" | "error") => void
}) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    const text = JSON.stringify(data, null, 2)
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        const ta = document.createElement("textarea")
        ta.value = text
        ta.style.position = "fixed"
        ta.style.opacity = "0"
        document.body.appendChild(ta)
        ta.select()
        document.execCommand("copy")
        document.body.removeChild(ta)
      }
      setCopied(true)
      onToast?.("Copied JSON to clipboard", "success")
      window.setTimeout(() => setCopied(false), 1500)
    } catch (e) {
      onToast?.((e as Error).message || "Failed to copy", "error")
    }
  }
  return (
    <Button
      size="small"
      variant="outlined"
      startIcon={
        copied ? (
          <CheckIcon fontSize="small" />
        ) : (
          <ContentCopyIcon fontSize="small" />
        )
      }
      onClick={copy}
      color={copied ? "success" : "primary"}
    >
      {copied ? "Copied" : "Copy"}
    </Button>
  )
}

function ItemsCell({ order }: { order: Order }) {
  const items = order.document_metadata?.items ?? []
  if (items.length === 0)
    return (
      <Typography component="span" color="text.disabled">
        —
      </Typography>
    )
  const first = items[0]
  const more = items.length - 1
  return (
    <Stack
      direction="row"
      spacing={0.75}
      alignItems="center"
      sx={{ maxWidth: 280 }}
    >
      <Typography
        variant="body2"
        noWrap
        title={items.map(describeItem).join("\n")}
      >
        {describeItem(first)}
      </Typography>
      {more > 0 && (
        <Chip
          label={`+${more}`}
          size="small"
          sx={{ height: 20, fontSize: 11, fontWeight: 600 }}
        />
      )}
    </Stack>
  )
}

export function OrdersPanel({ refreshKey, onToast }: Props) {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<OrderCreate>({
    patient_first_name: "",
    patient_last_name: "",
    patient_dob: "",
    status: "pending",
    notes: "",
  })
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Order | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const toggleExpand = (id: string) =>
    setExpandedId((c) => (c === id ? null : id))

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.listOrders({
        limit: 100,
        search: search || undefined,
        status: statusFilter || undefined,
      })
      setOrders(Array.isArray(r?.items) ? r.items : [])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load() /* eslint-disable-line */
  }, [refreshKey])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    try {
      await api.createOrder({
        ...form,
        patient_dob: form.patient_dob || null,
        notes: form.notes || null,
      })
      setForm({
        patient_first_name: "",
        patient_last_name: "",
        patient_dob: "",
        status: "pending",
        notes: "",
      })
      setShowCreate(false)
      onToast?.("Order created", "success")
      await load()
    } catch (e) {
      onToast?.((e as Error).message, "error")
    } finally {
      setCreating(false)
    }
  }

  const startEdit = (o: Order) => {
    setEditingId(o.id)
    setEditForm({ ...o })
  }

  const saveEdit = async () => {
    if (!editForm || !editingId) return
    try {
      await api.updateOrder(editingId, {
        patient_first_name: editForm.patient_first_name,
        patient_last_name: editForm.patient_last_name,
        patient_dob: editForm.patient_dob || null,
        status: editForm.status,
        notes: editForm.notes || null,
      })
      onToast?.("Order updated", "success")
      setEditingId(null)
      setEditForm(null)
      await load()
    } catch (e) {
      onToast?.((e as Error).message, "error")
    }
  }

  const remove = async (id: string) => {
    if (!confirm("Delete this order? This cannot be undone.")) return
    try {
      await api.deleteOrder(id)
      onToast?.("Order deleted", "success")
      await load()
    } catch (e) {
      onToast?.((e as Error).message, "error")
    }
  }

  return (
    <>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="flex-end"
        sx={{ mb: 3, flexWrap: "wrap", rowGap: 2 }}
      >
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Orders
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Orders extracted from documents or created manually.
          </Typography>
        </Box>
        <Button variant="contained" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "Close" : "+ New order"}
        </Button>
      </Stack>

      <Collapse in={showCreate}>
        <Card sx={{ mb: 2.5 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              Create order
            </Typography>
            <Box component="form" onSubmit={create}>
              <Box
                sx={{
                  display: "grid",
                  gap: 2,
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "1fr 1fr",
                    lg: "repeat(4, 1fr)",
                  },
                  mb: 2,
                }}
              >
                <TextField
                  label="First name"
                  required
                  value={form.patient_first_name}
                  onChange={(e) =>
                    setForm({ ...form, patient_first_name: e.target.value })
                  }
                />
                <TextField
                  label="Last name"
                  required
                  value={form.patient_last_name}
                  onChange={(e) =>
                    setForm({ ...form, patient_last_name: e.target.value })
                  }
                />
                <TextField
                  label="Date of birth"
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  value={form.patient_dob ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, patient_dob: e.target.value })
                  }
                />
                <TextField
                  select
                  label="Status"
                  value={form.status}
                  onChange={(e) =>
                    setForm({ ...form, status: e.target.value as OrderStatus })
                  }
                >
                  {STATUSES.map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </TextField>
              </Box>
              <TextField
                label="Notes"
                multiline
                minRows={2}
                value={form.notes ?? ""}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                sx={{ mb: 2 }}
              />
              <Stack direction="row" spacing={1.5}>
                <Button type="submit" variant="contained" disabled={creating}>
                  {creating ? "Creating…" : "Create order"}
                </Button>
                <Button variant="outlined" onClick={() => setShowCreate(false)}>
                  Cancel
                </Button>
              </Stack>
            </Box>
          </CardContent>
        </Card>
      </Collapse>

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Stack
            direction="row"
            spacing={2}
            alignItems="center"
            justifyContent="space-between"
            sx={{ mb: 2, flexWrap: "wrap", rowGap: 1 }}
          >
            <Stack direction="row" spacing={1}>
              <TextField
                placeholder="Search by name…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && load()}
                sx={{ width: 240 }}
              />
              <TextField
                select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                sx={{ width: 160 }}
              >
                <MenuItem value="">All statuses</MenuItem>
                {STATUSES.map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
              <Button variant="outlined" onClick={load} disabled={loading}>
                {loading ? "Loading…" : "Refresh"}
              </Button>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {orders.length} order{orders.length === 1 ? "" : "s"}
            </Typography>
          </Stack>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {orders.length === 0 && !loading ? (
            <Box sx={{ py: 6, textAlign: "center" }}>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                No orders yet
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                Create one above or upload a PDF.
              </Typography>
            </Box>
          ) : (
            <TableContainer
              sx={{
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 1.5,
                overflow: "hidden",
              }}
            >
              <Table
                size="small"
                sx={{
                  "& th, & td": { py: 1.5, px: 2 },
                  "& tbody tr:last-of-type td": { borderBottom: "none" },
                }}
              >
                <TableHead>
                  <TableRow
                    sx={{
                      bgcolor: "grey.50",
                      "& th": {
                        fontWeight: 600,
                        fontSize: 11,
                        letterSpacing: 0.6,
                        textTransform: "uppercase",
                        color: "text.secondary",
                      },
                    }}
                  >
                    <TableCell sx={{ width: 48 }} />
                    <TableCell>Patient</TableCell>
                    <TableCell>DOB</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Origin</TableCell>
                    <TableCell>Items</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {orders.map((o) =>
                    editingId === o.id && editForm ? (
                      <TableRow key={o.id} sx={{ bgcolor: "warning.light" }}>
                        <TableCell />
                        <TableCell>
                          <Stack direction="row" spacing={1}>
                            <TextField
                              value={editForm.patient_first_name}
                              onChange={(e) =>
                                setEditForm({
                                  ...editForm,
                                  patient_first_name: e.target.value,
                                })
                              }
                              sx={{ width: 110 }}
                            />
                            <TextField
                              value={editForm.patient_last_name}
                              onChange={(e) =>
                                setEditForm({
                                  ...editForm,
                                  patient_last_name: e.target.value,
                                })
                              }
                              sx={{ width: 110 }}
                            />
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <TextField
                            type="date"
                            value={editForm.patient_dob ?? ""}
                            onChange={(e) =>
                              setEditForm({
                                ...editForm,
                                patient_dob: e.target.value,
                              })
                            }
                            sx={{ width: 150 }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            select
                            value={editForm.status}
                            onChange={(e) =>
                              setEditForm({
                                ...editForm,
                                status: e.target.value as OrderStatus,
                              })
                            }
                            sx={{ width: 130 }}
                          >
                            {STATUSES.map((s) => (
                              <MenuItem key={s} value={s}>
                                {s}
                              </MenuItem>
                            ))}
                          </TextField>
                        </TableCell>
                        <TableCell sx={{ color: "text.secondary" }}>
                          {o.source_document_name ?? "—"}
                        </TableCell>
                        <TableCell sx={{ color: "text.disabled" }}>—</TableCell>
                        <TableCell
                          sx={{ whiteSpace: "nowrap", color: "text.secondary" }}
                        >
                          {new Date(o.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell align="right">
                          <Stack
                            direction="row"
                            spacing={1}
                            justifyContent="flex-end"
                          >
                            <Button
                              size="small"
                              variant="contained"
                              onClick={saveEdit}
                            >
                              Save
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => {
                                setEditingId(null)
                                setEditForm(null)
                              }}
                            >
                              Cancel
                            </Button>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ) : (
                      <Fragment key={o.id}>
                        <TableRow
                          hover
                          sx={{ cursor: "pointer" }}
                          onClick={() => toggleExpand(o.id)}
                          selected={expandedId === o.id}
                        >
                          <TableCell>
                            <IconButton size="small">
                              {expandedId === o.id ? (
                                <KeyboardArrowDownIcon fontSize="small" />
                              ) : (
                                <KeyboardArrowRightIcon fontSize="small" />
                              )}
                            </IconButton>
                          </TableCell>
                          <TableCell>
                            <Box>
                              <Typography sx={{ fontWeight: 600 }}>
                                {o.patient_first_name} {o.patient_last_name}
                              </Typography>
                              {o.notes && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{ display: "block", mt: 0.25 }}
                                >
                                  {o.notes}
                                </Typography>
                              )}
                            </Box>
                          </TableCell>
                          <TableCell>
                            {o.patient_dob ?? (
                              <Typography
                                component="span"
                                color="text.disabled"
                              >
                                —
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={o.status}
                              size="small"
                              color={statusColor(o.status)}
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <OriginCell order={o} />
                          </TableCell>
                          <TableCell>
                            <ItemsCell order={o} />
                          </TableCell>
                          <TableCell
                            sx={{
                              whiteSpace: "nowrap",
                              color: "text.secondary",
                            }}
                          >
                            {new Date(o.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell
                            align="right"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Stack
                              direction="row"
                              spacing={0.5}
                              justifyContent="flex-end"
                            >
                              <IconButton
                                size="small"
                                onClick={() => startEdit(o)}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => remove(o.id)}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Stack>
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell
                            colSpan={8}
                            sx={{
                              p: 0,
                              borderBottom:
                                expandedId === o.id ? undefined : "none",
                            }}
                          >
                            <Collapse in={expandedId === o.id} unmountOnExit>
                              <Box
                                sx={{
                                  px: 3,
                                  py: 3,
                                  bgcolor: "grey.50",
                                  borderTop: "1px solid",
                                  borderColor: "divider",
                                }}
                              >
                                {o.source_document_name && (
                                  <Stack
                                    direction="row"
                                    spacing={1}
                                    alignItems="center"
                                    sx={{
                                      mb: 2.5,
                                      px: 1.5,
                                      py: 1,
                                      bgcolor: "background.paper",
                                      border: "1px solid",
                                      borderColor: "divider",
                                      borderRadius: 1,
                                      width: "fit-content",
                                    }}
                                  >
                                    <DescriptionIcon
                                      fontSize="small"
                                      color="primary"
                                    />
                                    <Typography
                                      variant="body2"
                                      color="text.secondary"
                                    >
                                      Source file:
                                    </Typography>
                                    <Typography
                                      variant="body2"
                                      sx={{ fontWeight: 600 }}
                                    >
                                      {o.source_document_name}
                                    </Typography>
                                  </Stack>
                                )}
                                {o.document_metadata ? (
                                  <DocumentDetailsView
                                    details={o.document_metadata}
                                  />
                                ) : (
                                  <Typography
                                    variant="body2"
                                    color="text.secondary"
                                  >
                                    No extracted document details for this
                                    order.
                                  </Typography>
                                )}
                                <Box sx={{ mt: 3 }}>
                                  <Stack
                                    direction="row"
                                    alignItems="center"
                                    justifyContent="space-between"
                                    sx={{ mb: 1.25 }}
                                  >
                                    <Typography
                                      variant="overline"
                                      sx={{
                                        color: "text.secondary",
                                        fontWeight: 700,
                                        letterSpacing: 0.6,
                                      }}
                                    >
                                      Raw order JSON
                                    </Typography>
                                    <RawJsonCopyButton
                                      data={o}
                                      onToast={onToast}
                                    />
                                  </Stack>
                                  <Box
                                    component="pre"
                                    sx={{
                                      m: 0,
                                      p: 2,
                                      bgcolor: "grey.900",
                                      color: "grey.100",
                                      borderRadius: 1.5,
                                      fontSize: 12,
                                      lineHeight: 1.55,
                                      fontFamily:
                                        "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                      maxHeight: 360,
                                      overflow: "auto",
                                      whiteSpace: "pre",
                                    }}
                                  >
                                    {JSON.stringify(o, null, 2)}
                                  </Box>
                                </Box>
                              </Box>
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      </Fragment>
                    ),
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </>
  )
}
