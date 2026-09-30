"""Four-file FastAPI demo: fixed events, simulated phone actions, SSE delivery."""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Relay Agent Demo")


def event(kind, delay=1.2, **data):
    return {"kind": kind, "delay": round(delay * 1.2, 3), **data}


def agent(agent_id, name, lane, task, depends=()):
    return event(
        "agent_start", id=agent_id, name=name, lane=lane,
        task=task, depends=list(depends),
    )


def complete(agent_id, result):
    return event("agent_done", id=agent_id, result=result)


def insight(title, detail, source="Demo assumption"):
    return event("insight", title=title, detail=detail, source=source)


def handoff(title, detail):
    return event("handoff", title=title, detail=detail)


def prompt(action_id, scene, title, body, button):
    return event(
        "phone_prompt", action_id=action_id, scene=scene,
        title=title, body=body, button=button,
    )


def tap(action_id):
    return event("phone_tap", action_id=action_id, delay=1.5)


def checklist(scene, title, body, items):
    return event(
        "phone_checklist", scene=scene, title=title, body=body,
        items=[{"id": item_id, "label": label, "detail": detail}
               for item_id, label, detail in items],
    )


def check(item_id):
    return event("phone_check", item_id=item_id, delay=1.35)


def replace_item(old_id, new_id, label, detail):
    return event(
        "phone_replace", old_id=old_id, new_id=new_id,
        label=label, detail=detail,
    )


def notice(title, body):
    return event("phone_notice", title=title, body=body)


def gate(title, required):
    return event("supervisor_gate", title=title, required=list(required), delay=1.6)


def phone_end(scene, title, body, lines):
    return event("phone_end", scene=scene, title=title, body=body, lines=list(lines))


VISA_DEPARTURE = [
    ("v_passport", "Passport and photo ID", "Check that the originals are in your document folder."),
    ("v_booking", "Appointment confirmation and QR code", "Open the email or offline screenshot; confirm time and address."),
    ("v_application", "Application form and photos", "Verify whether they are required and which format applies."),
    ("v_evidence", "Supporting documents and copies", "Check each item against the official list for your visa type."),
    ("v_payment", "Payment receipt or payment method", "Check the instructions in your appointment notice."),
    ("v_address", "Address, entrance, and route", "Recheck the live route so you reach the right entrance."),
    ("v_battery", "Phone battery and power bank", "Demo battery: 28%. Charge your phone and take a cable."),
    ("v_weather", "Umbrella and waterproof folder", "Demo weather: light rain. Keep paper documents dry."),
]

VISA_ARRIVAL = [
    ("v_arrive", "Confirm the correct location", "Match the address and entrance to the appointment email."),
    ("v_queue", "Check the sign-in instructions", "Follow on-site directions and keep the QR code handy."),
    ("v_submit", "Documents submitted", "Ask about a receipt, missing documents, and collection instructions."),
]

GROCERIES = [
    ("g_asparagus", "1 bunch of asparagus", "A warm side for the steak."),
    ("g_potato", "About 300 g of baby potatoes", "Demo: out of stock; replace with a ready-made salad."),
    ("g_lemon", "1 lemon", "For the vegetables."),
    ("g_butter", "1 small pack of butter", "Demo pantry does not have any."),
    ("g_garlic", "1 head of garlic", "Demo pantry does not have any."),
]

COOKING = [
    ("c_wash", "Wash asparagus and prepare salad", "Prepare the sides before the steak is ready."),
    ("c_steak", "Cook the steak and check doneness", "Follow your preferred safe cooking method."),
    ("c_plate", "Plate and eat dinner", "Demo dinner window: 19:30–20:00."),
    ("c_clean", "Clean the pan and counter", "Keep the study start close to 20:15."),
]

STUDY = [
    ("s_outline", "Review Chapter 10's outline and terms", "20:15–20:40; use your actual course materials."),
    ("s_practice", "Try 1–2 representative problems", "20:40–21:05; mark any sticking points."),
    ("s_recall", "Recall the material without notes", "21:05–21:30; write down open questions."),
    ("s_bag", "Pack for class and charge devices", "Confirm the room, route, laptop, and alarm."),
    ("s_stop", "Stop studying at the cutoff", "Demo cutoff: 22:00. Do not trade sleep for extra tasks."),
]

WORKFLOWS = {
    "visa": {
        "title": "Visa document appointment",
        "subtitle": "October 1, 14:30 · Before leaving, travel, and on-site check-in",
        "summary": "Demo: reminder at 12:40, leave at 12:55, arrive at 14:00. Verify the real address, document rules, traffic, and battery level.",
        "steps": [
            agent("v_super", "Super Agent", "super", "Break the 14:30 appointment into schedule, travel, documents, and device checks."),
            insight("Known goal", "You provided a visa document appointment on October 1 at 14:30.", "User input"),
            agent("v_schedule", "Schedule Boss", "boss", "Check the demo calendar and find a departure window.", ["v_super"]),
            agent("v_travel", "Travel Boss", "boss", "Estimate the route, early arrival, and return trip.", ["v_super"]),
            agent("v_docs", "Documents Boss", "boss", "Build a departure checklist and flag unverified requirements.", ["v_super"]),
            agent("v_device", "Device Boss", "boss", "Check battery, QR access, and offline backup.", ["v_super"]),
            complete("v_super", "Four areas have been delegated; user confirmation will close the loop."),
            agent("v_calendar_worker", "Calendar Worker", "worker", "Read other events from a sample calendar.", ["v_schedule"]),
            complete("v_calendar_worker", "Sample calendar: meeting 10:00–11:00 and another event at 18:30."),
            insight("Other plans today", "The sample calendar has a 10:00–11:00 meeting and an 18:30 event. The appointment must fit around both.", "Sample calendar"),
            complete("v_schedule", "There is time after 11:00 for lunch, documents, and departure."),
            agent("v_route_worker", "Route Worker", "worker", "Use a sample 45-minute trip plus 20 minutes of slack.", ["v_travel"]),
            complete("v_route_worker", "14:00 arrival − 45-minute trip − 20-minute buffer = 12:55 departure."),
            insight("Leave and return", "Demo: leave at 12:55 and arrive at 14:00. With a 60-minute appointment and 45-minute return, home is about 16:15.", "Demo calculation"),
            agent("v_material_worker", "Checklist Worker", "worker", "Create a departure list without pretending to know official visa rules.", ["v_docs"]),
            complete("v_material_worker", "The list covers ID, booking, forms, evidence, payment, address, and rain protection."),
            agent("v_battery_worker", "Battery Worker", "worker", "Use a sample 28% battery and prepare charging and offline backup.", ["v_device"]),
            complete("v_battery_worker", "Charge toward 80%; take a power bank and save QR and address screenshots."),
            insight("Device and weather", "Demo battery: 28%; demo weather: light rain. Charge up and protect paper documents.", "Simulated status"),
            handoff("Agent plan → phone reminder", "It is now 12:40 in the demo: 15 minutes before the planned departure."),
            prompt("v_confirm_15", "Before leaving · 12:40", "Leave in 15 minutes?", "Your appointment is at 14:30. The sample trip takes 45 minutes with a 20-minute buffer, so leave at 12:55.", "Yes, get ready"),
            tap("v_confirm_15"),
            checklist("Before leaving", "Check the essentials", "The simulated user ticks items one by one. Supervisor reads these states, not just the Agent's text.", VISA_DEPARTURE),
            check("v_passport"),
            check("v_application"),
            check("v_evidence"),
            check("v_payment"),
            check("v_address"),
            check("v_battery"),
            check("v_weather"),
            agent("v_supervisor_1", "Supervisor", "supervisor", "Check the phone confirmation and eight departure items.", ["v_docs", "v_travel", "v_device"]),
            gate("Pre-departure check", ["v_confirm_15"] + [item[0] for item in VISA_DEPARTURE]),
            notice("Not ready to leave yet", "The simulated user has not checked the appointment confirmation and QR code. Documents Boss must resolve it."),
            handoff("Supervisor → Documents Boss", "The missing piece is a user confirmation on the phone, not another generic reminder."),
            agent("v_recover", "Booking Worker", "worker", "Find the booking email and save the QR code and address offline.", ["v_docs"]),
            complete("v_recover", "The simulated user found the email and saved an offline screenshot."),
            check("v_booking"),
            gate("Pre-departure recheck", ["v_confirm_15"] + [item[0] for item in VISA_DEPARTURE]),
            complete("v_supervisor_1", "All 8 items and the departure confirmation are complete."),
            complete("v_docs", "Phone checklist complete; actual official document rules still need personal verification."),
            complete("v_device", "Battery and offline backup have been acknowledged on the phone."),
            prompt("v_left_home", "On the way · 12:55", "Have you left home?", "Start navigation now, and watch for real traffic that differs from the 45-minute sample.", "I have left"),
            tap("v_left_home"),
            agent("v_monitor", "Journey Worker", "worker", "Pass the departure confirmation to Travel Boss and wait for arrival.", ["v_travel"]),
            complete("v_monitor", "The simulated user confirmed departure at 12:55."),
            prompt("v_reached_center", "Arrival · 14:00", "Have you reached the visa center?", "Match the entrance to your booking email, then follow the on-site sign-in instructions.", "I have arrived"),
            tap("v_reached_center"),
            checklist("At the visa center", "Three final steps", "The simulated user keeps confirming items after arrival.", VISA_ARRIVAL),
            check("v_arrive"),
            check("v_queue"),
            check("v_submit"),
            agent("v_supervisor_2", "Supervisor", "supervisor", "Check departure, arrival, and on-site submission states.", ["v_travel"]),
            gate("On-site check", ["v_left_home", "v_reached_center"] + [item[0] for item in VISA_ARRIVAL]),
            complete("v_supervisor_2", "On-site checklist 3/3. The demo submission is complete."),
            complete("v_travel", "Departure and arrival are confirmed. The real return time depends on the appointment."),
            phone_end(
                "Today's trip · Complete", "Visa submission simulated",
                "Departure, arrival, and on-site items have all been confirmed.",
                ["Demo: leave 12:55 · arrive 14:00", "Home around 16:15 if the appointment runs on time", "Keep the receipt and any follow-up instructions"],
            ),
        ],
    },
    "evening": {
        "title": "Steak dinner and ML review",
        "subtitle": "Tonight · Grocery store, cooking, Chapter 10, and tomorrow's 9:00 lecture",
        "summary": "Demo: grocery run at 18:00, cook at 19:00, review at 20:15, stop at 22:00; leave at 8:15 tomorrow. Adjust to real conditions.",
        "steps": [
            agent("e_super", "Super Agent", "super", "Connect groceries, cooking, review, and tomorrow's class in one timeline."),
            insight("Known constraints", "You want steak tonight, have no side dishes, need to review ML Chapter 10, and have a 9:00 lecture tomorrow.", "User input"),
            agent("e_food", "Dinner Boss", "boss", "Resolve missing ingredients and order the cooking steps.", ["e_super"]),
            agent("e_study", "Study Boss", "boss", "Break Chapter 10 into tasks that can be checked off.", ["e_super"]),
            agent("e_schedule", "Schedule Boss", "boss", "Set a stopping point and work backward from tomorrow's class.", ["e_super"]),
            complete("e_super", "Three workstreams are delegated; the phone will ask for confirmation at each stage."),
            agent("e_calendar_worker", "Calendar Worker", "worker", "Use a sample calendar with no other events tonight and class at 9:00.", ["e_schedule"]),
            complete("e_calendar_worker", "Demo commute: 35 minutes plus 10 minutes of buffer; leave at 8:15."),
            insight("Rest and commute", "Demo: stop studying at 22:00, go to bed by 23:00, wake at 7:15, and leave at 8:15.", "Demo calculation"),
            complete("e_schedule", "Rest and tomorrow's class are treated as hard constraints."),
            agent("e_pantry_worker", "Pantry Worker", "worker", "Sample pantry: steak, salt, and pepper; no sides, butter, or garlic.", ["e_food"]),
            complete("e_pantry_worker", "Buy asparagus, baby potatoes, lemon, butter, and garlic."),
            insight("Grocery window", "The demo starts at 18:00 and allows 45 minutes for the round trip and shopping. Store hours and stock are unverified.", "Demo assumption"),
            handoff("Dinner Boss → phone reminder", "First ask whether to go to the store. Show the list only after arrival is confirmed."),
            prompt("e_go_store", "Dinner · 18:00", "No side dishes. Go to the store?", "The sample grocery run takes about 45 minutes. Buy the sides before dinner crowds out study and sleep.", "Yes, go shopping"),
            tap("e_go_store"),
            prompt("e_at_store", "Shopping · 18:15", "Have you reached the store?", "The shopping list appears only after you arrive, keeping the earlier screen simple.", "I am at the store"),
            tap("e_at_store"),
            checklist("At the grocery store", "Ingredients for tonight", "The simulated user checks off each item as it goes into the basket.", GROCERIES),
            check("g_asparagus"),
            check("g_lemon"),
            check("g_butter"),
            check("g_garlic"),
            agent("e_supervisor_1", "Supervisor", "supervisor", "Check store arrival and the grocery checklist.", ["e_food"]),
            gate("Grocery check", ["e_go_store", "e_at_store"] + [item[0] for item in GROCERIES]),
            notice("Baby potatoes are out of stock", "The simulated user has not checked off potatoes. Supervisor cannot mark the grocery task complete."),
            handoff("Supervisor → Dinner Boss", "Substitute a ready-made salad to protect dinner and study time."),
            agent("e_substitute", "Substitution Worker", "worker", "Replace the potatoes with one bag of ready-made salad.", ["e_food"]),
            complete("e_substitute", "The out-of-stock item has been replaced on the shopping list."),
            replace_item("g_potato", "g_salad", "1 bag of ready-made salad", "Replaces the potatoes and needs no cooking."),
            check("g_salad"),
            gate("Grocery recheck", ["e_go_store", "e_at_store", "g_asparagus", "g_salad", "g_lemon", "g_butter", "g_garlic"]),
            complete("e_supervisor_1", "All 5 ingredients in the revised list are checked."),
            complete("e_food", "Shopping is done; hand off to cooking."),
            prompt("e_home", "Back home · 18:45", "Home and ready to cook?", "Wash the asparagus and prepare the salad first. The demo targets dinner by 20:00.", "Start cooking"),
            tap("e_home"),
            agent("e_cook", "Cooking Worker", "worker", "Turn dinner into four checkable phone actions.", ["e_food"]),
            checklist("Cooking dinner", "Finish dinner in order", "The simulated user checks each step before moving on to study.", COOKING),
            check("c_wash"),
            check("c_steak"),
            check("c_plate"),
            check("c_clean"),
            agent("e_supervisor_2", "Supervisor", "supervisor", "Check the return-home confirmation and cooking list.", ["e_food"]),
            gate("Dinner check", ["e_home"] + [item[0] for item in COOKING]),
            complete("e_supervisor_2", "Cooking 4/4; the study stage may begin."),
            complete("e_cook", "Demo dinner and basic cleanup finish before 20:00."),
            agent("e_chapter_worker", "Review Worker", "worker", "Use concepts, practice, and recall without guessing Chapter 10's subject.", ["e_study"]),
            complete("e_chapter_worker", "Demo review runs 20:15–21:30, with a firm 22:00 cutoff."),
            insight("Chapter 10 review", "Spend 25 minutes on concepts, 25 on practice, and 25 recalling without notes. Save open questions for tomorrow.", "Demo plan"),
            prompt("e_start_study", "Study · 20:15", "Start reviewing Chapter 10?", "Dinner is confirmed complete. Review for 75 minutes, then pack for tomorrow.", "Start review"),
            tap("e_start_study"),
            checklist("ML Chapter 10", "Tonight's study list", "The simulated user completes each item and adds no new tasks after the cutoff.", STUDY),
            check("s_outline"),
            check("s_practice"),
            check("s_recall"),
            check("s_bag"),
            check("s_stop"),
            agent("e_supervisor_3", "Supervisor", "supervisor", "Check study, tomorrow's preparation, and the cutoff.", ["e_study", "e_schedule"]),
            gate("Evening wrap-up check", ["e_start_study"] + [item[0] for item in STUDY]),
            complete("e_supervisor_3", "Study 5/5; stop at 22:00 and leave at 8:15 tomorrow."),
            complete("e_study", "Review and morning preparation were confirmed on the phone."),
            phone_end(
                "Tonight · Complete", "Dinner and review are done",
                "The demo plan is complete. Adjust it to the real time and conditions.",
                ["Stop studying at 22:00 · rest by 23:00", "Wake at 7:15 · leave at 8:15 tomorrow", "If shopping runs late, shorten review blocks rather than sleep"],
            ),
        ],
    },
}


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "index.html", media_type="text/html")


@app.get("/style.css")
def stylesheet():
    return FileResponse(BASE_DIR / "style.css", media_type="text/css")


@app.get("/app.js")
def javascript():
    return FileResponse(BASE_DIR / "app.js", media_type="text/javascript")


@app.get("/api/workflows/{workflow_id}/stream")
async def stream_workflow(workflow_id: str, request: Request):
    workflow = WORKFLOWS.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Unknown workflow")

    async def events():
        completed = set()
        labels = {}
        opening = {
            "kind": "workflow_start",
            "title": workflow["title"],
            "subtitle": workflow["subtitle"],
            "total": len(workflow["steps"]),
        }
        yield "event: workflow\ndata: " + json.dumps(opening, ensure_ascii=False) + "\n\n"

        for item in workflow["steps"]:
            await asyncio.sleep(item["delay"])
            if await request.is_disconnected():
                return

            payload = {key: value for key, value in item.items() if key != "delay"}
            kind = payload["kind"]
            if kind == "phone_prompt":
                labels[payload["action_id"]] = payload["button"]
            elif kind == "phone_checklist":
                labels.update({entry["id"]: entry["label"] for entry in payload["items"]})
            elif kind == "phone_replace":
                labels[payload["new_id"]] = payload["label"]
            elif kind == "phone_tap":
                completed.add(payload["action_id"])
            elif kind == "phone_check":
                completed.add(payload["item_id"])
            elif kind == "supervisor_gate":
                required = payload.pop("required")
                missing = [key for key in required if key not in completed]
                payload = {
                    "kind": "audit",
                    "title": payload["title"],
                    "status": "needs_work" if missing else "passed",
                    "checked": len(required) - len(missing),
                    "total": len(required),
                    "missing": [labels.get(key, key) for key in missing],
                }
            yield "event: workflow\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"

        closing = {"kind": "workflow_complete", "summary": workflow["summary"]}
        yield "event: workflow\ndata: " + json.dumps(closing, ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
