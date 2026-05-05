import { Fragment, useEffect, useState } from "react"
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Collapse,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Button,
  Paper,
} from "@mui/material"
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown"
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight"
import { api } from "../lib/api"
import { DocumentDetailsView } from "./DocumentDetailsView"
import type { Order, Patient } from "../types/api"

interface Props {
  refreshKey: number
  onToast?: (msg: string, kind?: "success" | "error") => void
}

export function PatientsPanel({ refreshKey, onToast }: Props) {
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")

  const [openId, setOpenId] = useState<string | null>(null)
  const [openOrders, setOpenOrders] = useState<Order[]>([])
  const [openLoading, setOpenLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.listPatients({
        limit: 100,
        search: search || undefined,
      })
      setPatients(Array.isArray(r?.items) ? r.items : [])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey])

  const togglePatient = async (p: Patient) => {
    if (openId === p.id) {
      setOpenId(null)
      setOpenOrders([])
      return
    }
    setOpenId(p.id)
    setOpenOrders([])
    setOpenLoading(true)
    try {
      const r = await api.listPatientOrders(p.id)
      setOpenOrders(Array.isArray(r?.items) ? r.items : [])
    } catch (e) {
      onToast?.((e as Error).message, "error")
    } finally {
      setOpenLoading(false)
    }
  }

  return (
    <>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Patients
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Unique patients derived from orders.
        </Typography>
      </Box>

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
                placeholder="Search by first name, last name, dob"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && load()}
                sx={{ width: 520 }}
              />
              <Button variant="outlined" onClick={load} disabled={loading}>
                {loading ? "Loading…" : "Refresh"}
              </Button>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {patients.length} patient{patients.length === 1 ? "" : "s"}
            </Typography>
          </Stack>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {patients.length === 0 && !loading ? (
            <Box sx={{ py: 6, textAlign: "center" }}>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                No patients yet
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                Upload a PDF or create an order to populate this list.
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
                    <TableCell align="right">Orders</TableCell>
                    <TableCell>First seen</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {patients.map((p) => (
                    <Fragment key={p.id}>
                      <TableRow
                        hover
                        sx={{ cursor: "pointer" }}
                        onClick={() => togglePatient(p)}
                        selected={openId === p.id}
                      >
                        <TableCell>
                          <IconButton size="small">
                            {openId === p.id ? (
                              <KeyboardArrowDownIcon fontSize="small" />
                            ) : (
                              <KeyboardArrowRightIcon fontSize="small" />
                            )}
                          </IconButton>
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>
                          {p.first_name} {p.last_name}
                        </TableCell>
                        <TableCell>
                          {p.dob ?? (
                            <Typography component="span" color="text.disabled">
                              —
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={p.order_count}
                            size="small"
                            color="primary"
                            sx={{
                              minWidth: 32,
                              fontWeight: 600,
                              bgcolor: "primary.light",
                              color: "primary.dark",
                            }}
                          />
                        </TableCell>
                        <TableCell sx={{ color: "text.secondary" }}>
                          {new Date(p.created_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell
                          colSpan={5}
                          sx={{
                            p: 0,
                            borderBottom: openId === p.id ? undefined : "none",
                          }}
                        >
                          <Collapse in={openId === p.id} unmountOnExit>
                            <Box sx={{ p: 0, bgcolor: "grey.50" }}>
                              {openLoading ? (
                                <Typography
                                  variant="body2"
                                  color="text.secondary"
                                  sx={{ p: 2 }}
                                >
                                  Loading orders…
                                </Typography>
                              ) : openOrders.length === 0 ? (
                                <Typography
                                  variant="body2"
                                  color="text.secondary"
                                  sx={{ p: 2 }}
                                >
                                  No orders for this patient.
                                </Typography>
                              ) : (
                                <Stack spacing={0}>
                                  {openOrders.map((o) => (
                                    <Paper
                                      key={o.id}
                                      square
                                      elevation={0}
                                      sx={{
                                        p: 2.5,
                                        bgcolor: "transparent",
                                        borderTop: "1px solid",
                                        borderColor: "divider",
                                        "&:first-of-type": {
                                          borderTop: "none",
                                        },
                                      }}
                                    >
                                      <Stack
                                        direction="row"
                                        spacing={1}
                                        alignItems="center"
                                        justifyContent="space-between"
                                        sx={{
                                          mb: 1,
                                          flexWrap: "wrap",
                                          rowGap: 1,
                                        }}
                                      >
                                        <Stack
                                          direction="row"
                                          spacing={1.5}
                                          alignItems="center"
                                        >
                                          <Typography
                                            variant="body2"
                                            color="text.secondary"
                                          >
                                            {new Date(
                                              o.created_at,
                                            ).toLocaleString()}
                                          </Typography>
                                          <Chip
                                            label={o.id.slice(0, 8)}
                                            size="small"
                                            sx={{
                                              fontFamily:
                                                "ui-monospace, monospace",
                                              fontSize: 11,
                                              height: 20,
                                            }}
                                          />
                                        </Stack>
                                        <Stack
                                          direction="row"
                                          spacing={1}
                                          alignItems="center"
                                        >
                                          <Chip
                                            label={o.status}
                                            size="small"
                                            color={
                                              o.status === "completed"
                                                ? "success"
                                                : o.status === "cancelled"
                                                  ? "error"
                                                  : o.status === "processing"
                                                    ? "info"
                                                    : "warning"
                                            }
                                            variant="outlined"
                                          />
                                          {o.source_document_name && (
                                            <Typography
                                              variant="caption"
                                              color="text.secondary"
                                            >
                                              {o.source_document_name}
                                            </Typography>
                                          )}
                                        </Stack>
                                      </Stack>
                                      <DocumentDetailsView
                                        details={o.document_metadata}
                                      />
                                    </Paper>
                                  ))}
                                </Stack>
                              )}
                            </Box>
                          </Collapse>
                        </TableCell>
                      </TableRow>
                    </Fragment>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </>
  )
}
