import { useEffect, useState } from "react"
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
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
} from "@mui/material"
import { api } from "../lib/api"
import type { ActivityLog } from "../types/api"

interface Props {
  refreshKey: number
}

const statusColor = (
  code: number,
): "success" | "info" | "warning" | "error" => {
  if (code < 300) return "success"
  if (code < 400) return "info"
  if (code < 500) return "warning"
  return "error"
}

export function ActivityPanel({ refreshKey }: Props) {
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pathFilter, setPathFilter] = useState("")

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.listActivityLogs({
        limit: 100,
        pathContains: pathFilter || undefined,
      })
      setLogs(Array.isArray(r?.items) ? r.items : [])
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

  return (
    <>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Activity
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Audit trail of every actions performed.
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
                placeholder="Filter by path…"
                value={pathFilter}
                onChange={(e) => setPathFilter(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && load()}
                sx={{ width: 520 }}
              />
              <Button variant="outlined" onClick={load} disabled={loading}>
                {loading ? "Loading…" : "Refresh"}
              </Button>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {logs.length} record{logs.length === 1 ? "" : "s"}
            </Typography>
          </Stack>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {logs.length === 0 && !loading ? (
            <Box sx={{ py: 6, textAlign: "center" }}>
              <Typography variant="body2" color="text.secondary">
                No activity recorded yet.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Resource</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell>Path</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Actor</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {logs.map((l) => (
                    <TableRow key={l.id} hover>
                      <TableCell
                        sx={{ whiteSpace: "nowrap", color: "text.secondary" }}
                      >
                        {new Date(l.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        {l.action ?? (
                          <Typography component="span" color="text.disabled">
                            —
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ color: "text.secondary" }}>
                        {l.resource_type ? (
                          <>
                            {l.resource_type}
                            {l.resource_id && (
                              <Chip
                                label={l.resource_id.slice(0, 8)}
                                size="small"
                                sx={{
                                  ml: 1,
                                  height: 18,
                                  fontFamily: "ui-monospace, monospace",
                                  fontSize: 10,
                                }}
                              />
                            )}
                          </>
                        ) : (
                          <Typography component="span" color="text.disabled">
                            —
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={l.method}
                          size="small"
                          sx={{
                            fontFamily: "ui-monospace, monospace",
                            fontSize: 11,
                            height: 20,
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={l.path}
                          size="small"
                          sx={{
                            fontFamily: "ui-monospace, monospace",
                            fontSize: 11,
                            height: 20,
                            maxWidth: 280,
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={l.status_code}
                          size="small"
                          color={statusColor(l.status_code)}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell
                        sx={{ whiteSpace: "nowrap", color: "text.secondary" }}
                      >
                        {l.duration_ms} ms
                      </TableCell>
                      <TableCell sx={{ color: "text.secondary" }}>
                        {l.actor ?? "—"}
                      </TableCell>
                    </TableRow>
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
