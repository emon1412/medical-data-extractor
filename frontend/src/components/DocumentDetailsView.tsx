import {
  Box,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material"
import type { Address, DocumentDetails } from "../types/api"

interface Props {
  details: DocumentDetails | null | undefined
}

function formatAddress(a: Address | null | undefined): string | null {
  if (!a) return null
  const lines = [
    a.line1,
    a.line2,
    [a.city, a.state, a.postal_code].filter(Boolean).join(", "),
  ].filter((s): s is string => !!s && s.trim().length > 0)
  return lines.length ? lines.join("\n") : null
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <Typography
      variant="caption"
      sx={{
        display: "block",
        mb: 1,
        fontWeight: 600,
        letterSpacing: 1,
        textTransform: "uppercase",
      }}
      color="text.secondary"
    >
      {children}
    </Typography>
  )
}

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={2} sx={{ mb: 0.75 }}>
      <Typography
        variant="body2"
        sx={{ minWidth: 140, fontWeight: 600 }}
        color="text.secondary"
      >
        {label}
      </Typography>
      <Box sx={{ flex: 1, whiteSpace: "pre-line" }}>
        {value ?? (
          <Typography component="span" color="text.disabled">
            —
          </Typography>
        )}
      </Box>
    </Stack>
  )
}

function CodeChip({
  value,
  color = "default",
}: {
  value: string
  color?: "default" | "primary"
}) {
  return (
    <Chip
      label={value}
      size="small"
      color={color}
      sx={{
        fontFamily: "ui-monospace, SFMono-Regular, monospace",
        fontSize: 11,
        height: 20,
      }}
    />
  )
}

export function DocumentDetailsView({ details }: Props) {
  if (!details) {
    return (
      <Box
        sx={{
          border: "1px dashed",
          borderColor: "divider",
          px: 2,
          py: 1.5,
          borderRadius: 1.5,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          No additional document fields were extracted.
        </Typography>
      </Box>
    )
  }

  const addr = formatAddress(details.patient_address)
  const presAddr = formatAddress(details.prescriber?.address)

  return (
    <Stack spacing={2.5}>
      {(details.document_type || details.order_date) && (
        <Box>
          <SectionHeading>Document</SectionHeading>
          {details.document_type && (
            <FieldRow label="Type" value={details.document_type} />
          )}
          {details.order_date && (
            <FieldRow label="Order date" value={details.order_date} />
          )}
        </Box>
      )}

      {addr && (
        <Box>
          <SectionHeading>Patient address</SectionHeading>
          <Typography sx={{ whiteSpace: "pre-line" }}>{addr}</Typography>
        </Box>
      )}

      {details.prescriber &&
        (details.prescriber.name ||
          details.prescriber.npi ||
          details.prescriber.phone ||
          details.prescriber.fax ||
          presAddr) && (
          <Box>
            <SectionHeading>Prescriber</SectionHeading>
            <FieldRow label="Name" value={details.prescriber.name} />
            {details.prescriber.npi && (
              <FieldRow
                label="NPI"
                value={<CodeChip value={details.prescriber.npi} />}
              />
            )}
            {details.prescriber.phone && (
              <FieldRow label="Phone" value={details.prescriber.phone} />
            )}
            {details.prescriber.fax && (
              <FieldRow label="Fax" value={details.prescriber.fax} />
            )}
            {presAddr && <FieldRow label="Address" value={presAddr} />}
          </Box>
        )}

      {details.diagnoses.length > 0 && (
        <Box>
          <SectionHeading>Diagnoses</SectionHeading>
          <Stack spacing={0.75}>
            {details.diagnoses.map((d, i) => (
              <Stack key={i} direction="row" spacing={1} alignItems="baseline">
                {d.code && <CodeChip value={d.code} color="primary" />}
                <Typography>{d.description ?? ""}</Typography>
              </Stack>
            ))}
          </Stack>
        </Box>
      )}

      {details.items.length > 0 && (
        <Box>
          <SectionHeading>Items ordered</SectionHeading>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Code</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Side</TableCell>
                <TableCell align="right">Qty</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {details.items.map((it, i) => (
                <TableRow key={i}>
                  <TableCell>
                    {it.code ? (
                      <CodeChip value={it.code} />
                    ) : (
                      <Typography component="span" color="text.disabled">
                        —
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {it.description ?? (
                      <Typography component="span" color="text.disabled">
                        —
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {it.side ?? (
                      <Typography component="span" color="text.disabled">
                        —
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {it.quantity ?? (
                      <Typography component="span" color="text.disabled">
                        —
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}
    </Stack>
  )
}
