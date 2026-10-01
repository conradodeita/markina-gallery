"""Inventário estático da task 1.3; não importa a aplicação nem acessa serviços/dados."""

import argparse
import ast
import hashlib
import re
from collections import Counter
from pathlib import Path

CHANGE = Path(__file__).resolve().parent
ROOT = CHANGE.parents[2]
OUTPUT = CHANGE / "ownership-inventory.md"

# R: proprietário persistido; D: filho com proprietário derivado e integridade;
# I: infraestrutura técnica; M: registro misto, exige discriminador de contexto.
TABLE_GROUPS = {
    ("I", "A"): "AdminUser Tenant AdminActionToken EmailDelivery EmailDeliveryAttempt",
    ("I", "O"): "InstallationOperator",
    ("D", "A"): "TenantAdmin",
    ("M", "A"): "AdminSecurityChallenge AuthChallenge AuthSession AuditEvent",
    ("R", "C"): "Client ClientDeletionReceipt",
    ("D", "C"): "ClientPhone",
    ("R", "G"): "GalleryAccess ParentGallery PhotoAsset DerivedGallery",
    ("D", "G"): (
        "ParentGalleryRegistration PhotoFolder GalleryClientState FolderClientGrant "
        "DerivedGalleryMembership DerivedGalleryPhoto DerivedGalleryPhotoOrigin "
        "GalleryAccessCapability PrivateUploadBatch PrivateUploadBatchAsset"
    ),
    ("R", "S"): "PaymentGroup SaleOrder RemovedPhotoMovement CommercialHistoryMedia",
    ("D", "S"): (
        "PhotoSelection PhotoFavorite PhotoView PhotoComment SaleOrderItem "
        "PaymentCommunication PaymentConfirmationCorrection GalleryReopeningRequest"
    ),
    ("R", "K"): (
        "BrandingSettings GlobalPixSettings PaymentMessageTemplate ProgressivePricingPreset "
        "WhatsAppChannelSettings PreviewAdjustmentSettings NotificationSetting"
    ),
    ("D", "K"): (
        "PriceRule PixCheckoutSettings ProgressivePricingTier GalleryPreviewSettings "
        "FolderProcessingSettings"
    ),
    ("R", "L"): "AssetFileCleanup GalleryLifecycleOperation",
    ("R", "N"): (
        "GalleryMembershipNotificationOutbox WhatsAppDelivery WhatsAppWebhookReceipt "
        "PushSubscription NotificationEvent"
    ),
    ("D", "N"): (
        "PaymentNotificationOutbox GalleryReopeningNotificationOutbox "
        "WhatsAppDeliveryAttempt NotificationMilestone NotificationDelivery"
    ),
    ("R", "P"): "MediaJob",
    ("D", "P"): "MediaDerivative PreviewAdjustment",
    ("R", "F"): (
        "FacialCalibrationApproval FacialRolloutOperation FacialJob FacialSearchRequest"
    ),
    ("D", "F"): (
        "GalleryFacialPolicy FacialRollout FacialLegalRepresentation PhotoAnalysis "
        "PhotoFaceEmbedding FacialSearchSnapshotItem FacialSearchCandidate "
        "FacialSearchNotificationOutbox"
    ),
}
MODELS = {name: group for group, names in TABLE_GROUPS.items() for name in names.split()}

MODULE_GROUPS = {
    "O": "installation_operator provision_installation_operator",
    "A": "auth admin_account admin_security tenancy seed_admin provision_photographer",
    "C": "client_identity",
    "G": (
        "gallery_access public_gallery_access parent_registration private_derivation "
        "private_membership private_upload_batches gallery_visuals acervo_context"
    ),
    "S": (
        "checkout client_commerce unified_checkout canonical_selection commercial_projection "
        "commercial_history order_delivery pricing pix"
    ),
    "K": "global_pix gallery_pricing payment_templates notification_settings branding_context",
    "L": (
        "asset_removal client_lifecycle commercial_removal commercial_retention gallery_cleanup "
        "gallery_lifecycle homolog_cleanup private_gallery_lifecycle"
    ),
    "N": (
        "email_delivery membership_notifications messaging notification_contract "
        "notification_delivery notification_events push_subscriptions web_push "
        "whatsapp_channel whatsapp_delivery whatsapp_webhook whatsapp_binding"
    ),
    "P": "media folder_processing folder_processing_api",
    "I": "product_brand public_origin",
    "X": "main worker historical_media ownership_schema storage_metrics",
}
MODULES = {name: group for group, names in MODULE_GROUPS.items() for name in names.split()}
SQL_NAMES = {"select", "insert", "update", "delete", "text"}
ORM_NAMES = {
    "query", "get", "scalar", "scalars", "execute", "add", "add_all", "delete", "merge",
    "bulk_insert_mappings", "bulk_update_mappings", "bulk_save_objects",
}
GATES = {
    "require_operator", "require_installation_operator", "operator_is_active",
    "require_single_tenant", "require_admin_tenant", "require_parent_tenant",
    "enable_domain_guard", "domain_session",
    "require_identity_tenant", "require_client_owner", "directory_tenant_id",
    "existing_admin_owner",
    "owned_record", "require_active_owner", "client_tenant_id",
    "legacy_owned_photographer_phone", "branding_tenant_id", "branding_settings",
    "require_security_owner", "require_media_photo", "media_namespace", "adjustment_for",
    "resolve_binding", "provider_for", "require_client_channel", "require_push_session", "webhook_owner",
}
HTTP_METHODS = {"get", "post", "patch", "put", "delete", "head", "options", "api_route"}
EFFECT_PATTERN = re.compile(
    r"send|publish|enqueue|dispatch|decrypt|encrypt|unlink|rmtree|remove_storage|"
    r"write_bytes|write_text|copyfile|copy2|\.replace$|\.rename$|\.open$|upload|download"
)
STATE_PATTERN = re.compile(
    r"cache|localStorage|sessionStorage|CacheStorage|caches\.|Redis|redis\.|setex|lpush|brpop",
    re.IGNORECASE,
)


def module_group(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if "/capacity_observability/" in relative:
        return "O"
    if "/facial/" in relative:
        return "F"
    if "/preview_adjustment/" in relative:
        return "P"
    if relative.startswith("scripts/"):
        return "T"
    if relative.startswith("frontend/"):
        return "U"
    if path.stem == "__init__":
        return "I"
    return MODULES[path.stem]  # Arquivo novo não classificado impede regeneração.


def owner_function(functions: list, node: ast.AST) -> str:
    matches = [
        item for item in functions if item.lineno <= node.lineno <= item.end_lineno
    ]
    return max(matches, key=lambda item: item.lineno).name if matches else "<módulo>"


def route_group(route: str, method: str) -> tuple[str, str]:
    if route == "/health":
        return "I", "I"
    if route in {"/admin/capacity-observability", "/admin/installation-capabilities", "/admin/facial-observability"}:
        return "I", "O"
    if route.startswith("/auth/"):
        return "M", "A"
    if route == "/admin" or route.startswith(("/admin/security/", "/admin/email/")):
        return "M", "A"
    if "facial" in route or "face-region" in route or "face-regions" in route:
        return "R", "F"
    if "preview-adjustment" in route or "/processing" in route:
        return "R", "P"
    if "branding" in route:
        return "M", "K"  # Público exige capacidade/contexto; admin exige membership.
    if any(part in route for part in (
        "settings/pix", "pricing", "notification-settings", "payment-message-templates",
    )):
        return "R", "K"
    if any(part in route for part in (
        "whatsapp", "push/", "notifications", "payment-notifications",
    )):
        return "R", "N"
    if any(part in route for part in (
        "deletion-inventory", "unlink-inventory", "lifecycle", "statistics", "export.",
        "validation-summary", "removed-photo-movements",
    )):
        return "R", "L"
    if route.startswith("/admin/clients"):
        return "R", "L" if method == "delete" else "C"
    if method == "delete" and route.startswith("/admin/") and any(
        part in route for part in ("/photos", "/photo-folders", "/clients/")
    ):
        return "R", "L"
    if any(part in route for part in (
        "/selection", "/favorite", "/view", "/comments", "/cart", "/checkout",
        "/orders", "/purchases", "/history", "/payment", "reopening", "/sales", "/review",
    )):
        return "R", "S"
    if route.startswith(("/admin/parent-galleries", "/admin/derived-galleries", "/admin/photo-",
                         "/gallery/", "/public-galleries/")) or route in ("/library", "/public-gallery/access"):
        return "R", "G"
    raise ValueError(f"Rota não classificada: {method} {route}")


def render() -> tuple[str, Counter]:
    sources = sorted((ROOT / "backend/app").rglob("*.py"))
    sources += sorted(path for path in (ROOT / "scripts").rglob("*") if path.suffix in {".py", ".sh"}
                      and not path.name.startswith("test_"))
    sources += sorted(path for path in (ROOT / "frontend/app").rglob("*")
                      if path.suffix in {".ts", ".tsx"} and ".test." not in path.name)
    sources += [ROOT / "frontend/public/markina-sw.js"]
    digest = hashlib.sha256()
    tables, modules, routes, sites, states = [], [], [], [], []
    count = Counter()
    found_models = set()
    for path in sources:
        relative = path.relative_to(ROOT).as_posix()
        content = path.read_bytes()
        digest.update(relative.encode() + b"\0" + content + b"\0")
        source = content.decode("utf-8-sig")
        group = module_group(path)
        modules.append(f"| `{relative}` | {group} | ver matriz |")
        for number, line in enumerate(source.splitlines(), 1):
            if STATE_PATTERN.search(line):
                states.append(f"| `{relative}:{number}` | {group} | armazenamento/cache/wake-up |")
        if path.suffix != ".py":
            # Shell/frontend: chamadas e efeitos são revisados por arquivo, sem parser Python.
            continue
        tree = ast.parse(source, filename=relative)
        functions = [node for node in ast.walk(tree)
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                table = next((statement.value.value for statement in node.body
                              if isinstance(statement, ast.Assign)
                              and isinstance(statement.value, ast.Constant)
                              and any(isinstance(target, ast.Name) and target.id == "__tablename__"
                                      for target in statement.targets)), None)
                if table:
                    kind, case = MODELS[node.name]
                    found_models.add(node.name)
                    refs = sorted({str(arg.value) for call in ast.walk(node)
                                   if isinstance(call, ast.Call)
                                   and ast.unparse(call.func) == "ForeignKey"
                                   for arg in call.args if isinstance(arg, ast.Constant)})
                    # FKs compostas são listadas pelo nome, sem copiar SQL/código/configuração.
                    refs += sorted({"composta:" + str(kw.value.value) for call in ast.walk(node)
                                    if isinstance(call, ast.Call)
                                    and ast.unparse(call.func) == "ForeignKeyConstraint"
                                    for kw in call.keywords if kw.arg == "name"
                                    and isinstance(kw.value, ast.Constant)})
                    tables.append(f"| `{table}` / `{node.name}` | {kind} | {case} | "
                                  f"`{relative}:{node.lineno}` | {'; '.join(refs) or 'sem FK'} | ver matriz |")
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr in HTTP_METHODS and decorator.args
                        and isinstance(decorator.args[0], ast.Constant)):
                    route = str(decorator.args[0].value)
                    dependencies = sorted({ast.unparse(arg) for call in ast.walk(node.args)
                                           if isinstance(call, ast.Call)
                                           and ast.unparse(call.func) == "Depends" for arg in call.args})
                    scope, case = route_group(route, decorator.func.attr)
                    routes.append(f"| `{decorator.func.attr.upper()} {route}` | {scope}/{case} | "
                                  f"`{relative}:{node.lineno}` / `{node.name}` | "
                                  f"{', '.join(dependencies) or 'sem Depends na assinatura'} | ver matriz |")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = ast.unparse(node.func)
            final = name.rsplit(".", 1)[-1]
            tags = []
            if final in MODELS:
                tags.append("produtor")
            if final in SQL_NAMES or (isinstance(node.func, ast.Attribute) and final in ORM_NAMES):
                tags.append("query/ORM")
            if final in GATES:
                tags.append("gate")
            if EFFECT_PATTERN.search(name):
                tags.append("efeito potencial")
            if tags:
                count.update(tags)
                sites.append(f"| `{relative}:{node.lineno}` / `{owner_function(functions, node)}` | "
                             f"{group} | {', '.join(tags)} | `{name}` | ver matriz |")
    if found_models != set(MODELS):
        raise ValueError(f"Classificação divergente: {sorted(found_models ^ set(MODELS))}")
    count.update(tabelas=len(tables), arquivos=len(sources), rotas=len(routes), estado=len(states), sitios=len(sites))
    lines = ["# Inventário de código — complemento da matriz", "",
             ("Gerado por `inventory_ownership.py`; consultar `ownership-matrix.md` para decisões, "
              "critérios A–X, testes e limites. Este inventário estático associa fontes a critérios; não executa testes nem decide prontidão. O estado e as evidências de implementação/validação estão na matriz e em `validation.md`."), "",
             f"SHA256 das fontes inventariadas: `{digest.hexdigest()}`.", "",
             "Contagens: " + "; ".join(f"{key}={value}" for key, value in sorted(count.items())) + ".", ""]
    for title, header, rows in (
        ("Tabelas", "Tabela/modelo | Classe | Critério/teste | Fonte | FKs atuais | Evidência por critério", tables),
        ("Arquivos e fronteiras", "Arquivo | Critério/teste | Evidência por critério", modules),
        ("Rotas HTTP", "Rota | Escopo/critério | Fonte/handler | Dependências atuais | Evidência por critério", routes),
        ("Produtores queries gates e efeitos", "Fonte/função | Critério/teste | Sinal | Chamada | Evidência por critério", sites),
        ("Cache estado local e wake-up", "Fonte | Critério/teste | Sinal", states),
    ):
        lines.extend([f"## {title}", "", "| " + header + " |",
                      "| " + " | ".join("---" for _ in header.strip("|").split("|")) + " |", *rows, ""])
    return "\n".join(lines), count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Confere sem escrever o inventário.")
    args = parser.parse_args()
    document, counts = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != document:
            raise SystemExit("Inventário desatualizado; regenerar e revisar a matriz.")
    else:
        OUTPUT.write_text(document, encoding="utf-8", newline="\n")
    print("Inventário conferido: " + "; ".join(f"{key}={value}" for key, value in sorted(counts.items())))
