{{- define "maintainai.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 50 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 50 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "maintainai.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "maintainai.selector" -}}
app.kubernetes.io/name: {{ .root.Chart.Name }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "maintainai.image" -}}
{{- $registry := .root.Values.image.registry -}}
{{- if $registry -}}
{{- printf "%s/maintainai-%s:%s" $registry .name .root.Values.image.tag -}}
{{- else -}}
{{- printf "maintainai-%s:%s" .name .root.Values.image.tag -}}
{{- end -}}
{{- end -}}

{{- define "maintainai.secretName" -}}
{{- default (printf "%s-secrets" (include "maintainai.fullname" .)) .Values.secrets.existingSecret -}}
{{- end -}}

{{- define "maintainai.dbHost" -}}
{{- if .Values.postgres.enabled -}}
{{- printf "%s-postgres" (include "maintainai.fullname" .) -}}
{{- else -}}
{{- required "externalDatabase.host is required when postgres.enabled=false" .Values.externalDatabase.host -}}
{{- end -}}
{{- end -}}

{{/* Environment shared by the Python services */}}
{{- define "maintainai.pythonEnv" -}}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "maintainai.secretName" . }}
      key: DATABASE_URL
- name: MISTRAL_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "maintainai.secretName" . }}
      key: MISTRAL_API_KEY
      optional: true
{{- end -}}

{{- define "maintainai.tmpVolumeMount" -}}
- name: tmp
  mountPath: /tmp
{{- end -}}

{{- define "maintainai.tmpVolume" -}}
- name: tmp
  emptyDir:
    sizeLimit: 64Mi
{{- end -}}

{{- define "maintainai.from" -}}
- podSelector:
    matchLabels:
      app.kubernetes.io/instance: {{ .root.Release.Name }}
      app.kubernetes.io/component: {{ .component }}
{{- end -}}
