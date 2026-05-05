import { useState } from "react"
import {
  AppBar,
  Box,
  Container,
  Tab,
  Tabs,
  Toolbar,
  Typography,
  Snackbar,
  Alert,
} from "@mui/material"
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined"
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined"
import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined"
import PeopleAltOutlinedIcon from "@mui/icons-material/PeopleAltOutlined"
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined"
import { OrdersPanel } from "./components/OrdersPanel"
import { UploadPanel } from "./components/UploadPanel"
import { PatientsPanel } from "./components/PatientsPanel"
import { ActivityPanel } from "./components/ActivityPanel"
import { LoginGate } from "./components/LoginGate"
import { setApiKey } from "./lib/api"

type Tab = "upload" | "orders" | "patients" | "activity"
type ToastKind = "success" | "error"

interface Toast {
  msg: string
  kind: ToastKind
}

const TABS: { id: Tab; label: string; icon: React.ReactElement }[] = [
  {
    id: "upload",
    label: "Upload",
    icon: <CloudUploadOutlinedIcon fontSize="small" />,
  },
  {
    id: "orders",
    label: "Orders",
    icon: <AssignmentOutlinedIcon fontSize="small" />,
  },
  {
    id: "patients",
    label: "Patients",
    icon: <PeopleAltOutlinedIcon fontSize="small" />,
  },
  {
    id: "activity",
    label: "Activity",
    icon: <HistoryOutlinedIcon fontSize="small" />,
  },
]

export default function App() {
  const [authed, setAuthed] = useState(false)
  const [tab, setTab] = useState<Tab>("upload")
  const [refreshKey, setRefreshKey] = useState(0)
  const [activityKey, setActivityKey] = useState(0)
  const [toast, setToast] = useState<Toast | null>(null)

  const showToast = (msg: string, kind: "success" | "error" = "success") => {
    setToast({ msg, kind })
  }
  const refreshOrders = () => setRefreshKey((n) => n + 1)
  const refreshActivity = () => setActivityKey((n) => n + 1)
  const goToOrders = () => setTab("orders")

  const signOut = () => {
    setApiKey("")
    setAuthed(false)
  }

  if (!authed) {
    return <LoginGate onAuthenticated={() => setAuthed(true)} />
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="sticky">
        <Container maxWidth="lg">
          <Toolbar disableGutters sx={{ gap: 3, py: 1 }}>
            <Box
              onClick={() => setTab("upload")}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                cursor: "pointer",
              }}
            >
              <Typography
                variant="h6"
                sx={{ fontWeight: 700, color: "text.primary" }}
              >
                Medical Order Extractor
              </Typography>
            </Box>
            <Box sx={{ flex: 1 }} />
            <Tabs
              value={tab}
              onChange={(_, v) => {
                if (v === "signout") {
                  signOut()
                  return
                }
                setTab(v as Tab)
              }}
              textColor="inherit"
            >
              {TABS.map((t) => (
                <Tab
                  key={t.id}
                  value={t.id}
                  label={t.label}
                  icon={t.icon}
                  iconPosition="start"
                  sx={{
                    color: "text.secondary",
                    minHeight: 40,
                    "&.Mui-selected": {
                      bgcolor: "primary.main",
                      color: "primary.contrastText",
                    },
                  }}
                />
              ))}
              <Tab
                key="signout"
                value="signout"
                label="Sign out"
                icon={<LogoutOutlinedIcon fontSize="small" />}
                iconPosition="start"
                sx={{
                  color: "text.secondary",
                  minHeight: 40,
                }}
              />
            </Tabs>
          </Toolbar>
        </Container>
      </AppBar>

      <Container maxWidth="lg" sx={{ pt: 5, pb: 10 }}>
        {tab === "upload" && (
          <UploadPanel
            onOrderCreated={() => {
              refreshOrders()
              refreshActivity()
            }}
            onToast={showToast}
            onViewOrders={goToOrders}
          />
        )}
        {tab === "orders" && (
          <OrdersPanel
            refreshKey={refreshKey}
            onToast={(m: string, k?: ToastKind) => {
              showToast(m, k)
              refreshActivity()
            }}
          />
        )}
        {tab === "patients" && (
          <PatientsPanel
            refreshKey={refreshKey}
            onToast={(m: string, k?: ToastKind) => {
              showToast(m, k)
              refreshActivity()
            }}
          />
        )}
        {tab === "activity" && <ActivityPanel refreshKey={activityKey} />}
      </Container>

      <Snackbar
        open={!!toast}
        autoHideDuration={3500}
        onClose={() => setToast(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        {toast ? (
          <Alert
            severity={toast.kind === "error" ? "error" : "success"}
            variant="filled"
            onClose={() => setToast(null)}
          >
            {toast.msg}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Box>
  )
}
