"""Generate data/transcripts/*.json: SYNTHETIC transcripts (invented people and firm).

Each file has an "expect" block with the flag codes the rubric must raise, written
by hand per scenario. Run: python3 tools/make_transcripts.py
"""
import json
import pathlib


def A(text, **kw):
    return {"speaker": "agent", "text": text, **kw}


def U(text, **kw):
    return {"speaker": "user", "text": text, **kw}


S = []


def add(id, lang, turns, expect, note):
    S.append((id, lang, turns, expect, note))


# ---------------------------------------------------------------- good calls
add("es_clean_booking", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte. ¿Hablo con el doctor?"),
    U("Sí, dígame."),
    A("Le llamo para ofrecerle una sesión corta de asesoría financiera, veinte minutos por videollamada. ¿Le interesaría?"),
    U("Sí, claro, suena bien."),
    A("¿Le queda mejor el jueves a las 4 o el viernes a las 10?"),
    U("El jueves a las 4."),
    A("Perfecto, quedó agendada para el jueves a las 4. Gracias, hasta luego.", tool="book_slot"),
], [], "Clear yes, slot chosen, booking, closing.")

add("en_clean_booking", "en", [
    A("Good afternoon, this is Sophie from North Studio. Am I speaking with the doctor?"),
    U("Speaking."),
    A("I'm calling about a short financial advisory session, twenty minutes over video. Would that interest you?"),
    U("Sure, that sounds good."),
    A("Does Thursday at 4 or Friday at 10 work better?"),
    U("Thursday at 4 works."),
    A("Done, you're booked for Thursday at 4. Have a great day.", tool="book_slot"),
], [], "Clear yes, booking.")

add("es_hedge_then_yes", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte, ¿hablo con el doctor?"),
    U("Sí, soy yo."),
    A("Le llamo para una sesión corta de asesoría, veinte minutos. ¿Le interesa?"),
    U("No sé, estoy ocupado."),
    A("Lo entiendo, son solo veinte minutos y podemos elegir un horario tranquilo. ¿Le parece?"),
    U("Sí, está bien, el jueves a las 5."),
    A("Perfecto, quedó agendada para el jueves a las 5. Hasta luego.", tool="book_slot"),
], [], "A hedge followed by a real yes is fine.")

add("es_one_no_then_yes", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte, ¿hablo con la doctora?"),
    U("Sí."),
    A("Le llamo para una sesión corta de asesoría. ¿Le interesaría?"),
    U("No, gracias."),
    A("Entiendo. Solo para que lo sepa, es sin costo y de veinte minutos. ¿Se la agendo?"),
    U("Ah, bueno, de acuerdo, el viernes a las 10."),
    A("Perfecto, quedó agendada el viernes a las 10. Gracias por su tiempo.", tool="book_slot"),
], [], "One refusal then a clear yes: not a violation.")

# ---------------------------------------------------------------- gatekeepers
add("es_gatekeeper_good", "es", [
    A("Buenas tardes, ¿hablo con el doctor?"),
    U("Soy la asistente, el doctor está en consulta. ¿De parte de quién?"),
    A("Le habla Sofía de Estudio Norte. Gracias, hasta luego.", tool="end_call"),
], [], "Name and firm in one turn, then closes.")

add("en_gatekeeper_good", "en", [
    A("Good afternoon, may I speak with the doctor?"),
    U("I'm his assistant, he's with a patient. Who's calling?"),
    A("This is Sophie from North Studio. Thank you for your time, goodbye.", tool="end_call"),
], [], "One turn and out.")

add("es_gatekeeper_chat", "es", [
    A("Buenas tardes, ¿hablo con el doctor?"),
    U("Soy la secretaria, el doctor no está. ¿De parte de quién?"),
    A("Le habla Sofía de Estudio Norte, ¿me podría decir cuándo lo encuentro?"),
    U("Tiene consulta toda la tarde."),
    A("Entiendo. Le cuento rápido de qué se trata: ofrecemos sesiones de asesoría financiera."),
    U("Ajá."),
    A("Son veinte minutos por videollamada y no tienen costo. ¿Cree que le interese al doctor?"),
    U("No sé, tendría que preguntarle."),
    A("¿Y usted podría decirme cuál es su horario libre?"),
], ["gatekeeper_chat"], "Agent keeps chatting with the receptionist.")

add("en_gatekeeper_chat", "en", [
    A("Hello, may I speak with the doctor?"),
    U("I'm the receptionist, he's not available. Can I take a message?"),
    A("Sure. I'm Sophie from North Studio. When is he usually free?"),
    U("Mornings, mostly."),
    A("Great. Let me tell you about our advisory sessions, they take twenty minutes."),
    U("Okay."),
    A("They're free and over video. Do you think he would like one?"),
], ["gatekeeper_chat"], "Pitching to the receptionist.")

add("es_gatekeeper_booked", "es", [
    A("Buenas tardes, ¿hablo con el doctor?"),
    U("Soy la asistente, ¿de qué se trata?"),
    A("Le habla Sofía de Estudio Norte, ofrecemos una sesión corta de asesoría financiera."),
    U("Ah, está bien, anote el jueves a las 4."),
    A("Perfecto, quedó agendada para el jueves a las 4.", tool="book_slot"),
    U("Gracias."),
    A("Gracias, hasta luego."),
], ["gatekeeper_booking", "gatekeeper_chat"], "Booked with the assistant, not the target (also a pitch plus a booking turn).")

add("es_gatekeeper_then_doctor", "es", [
    A("Buenas tardes, ¿hablo con el doctor?"),
    U("Soy la asistente, ¿de parte de quién?"),
    A("Sofía, de Estudio Norte. Si gusta, vuelvo a llamar. Hasta luego."),
    U("Espere, ya se lo paso."),
    U("Habla el doctor, dígame."),
    A("Doctor, le llamo para una sesión corta de asesoría, veinte minutos. ¿Le interesa?"),
    U("Sí, de acuerdo, el miércoles a las 3."),
    A("Perfecto, quedó agendada el miércoles a las 3. Gracias por su tiempo.", tool="book_slot"),
], [], "Booking happens after the doctor takes the phone.")

# ---------------------------------------------------------------- forced booking
add("es_forced_booking", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte, ¿hablo con el doctor?"),
    U("Sí, dígame."),
    A("Le llamo para una sesión corta de asesoría. ¿Le interesaría?"),
    U("No sé, tal vez, estoy ocupado ahorita."),
    A("Perfecto, entonces le dejo agendado el jueves a las 4. Quedó agendada, hasta luego.", tool="book_slot"),
], ["forced_booking"], "Hedge treated as a yes.")

add("en_forced_booking", "en", [
    A("Good afternoon, this is Sophie from North Studio. Is this the doctor?"),
    U("Yes."),
    A("I'm calling about a short advisory session. Would you be interested?"),
    U("Hmm, I'm busy right now, maybe."),
    A("Great, I've put you down for Thursday at 4. You're booked, goodbye.", tool="book_slot"),
], ["forced_booking"], "Booking on a maybe.")

add("es_booking_without_user_reply", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte."),
    A("Quedó agendada una sesión para el jueves a las 4.", tool="book_slot"),
], ["forced_booking"], "Booking with no user turn at all.")

# ---------------------------------------------------------------- interruptions
add("es_ignored_interruption", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte. Le llamo para ofrecerle una sesión corta de asesoría financiera por videollamada, veinte minutos, sin costo y sin compromiso alguno."),
    U("Espere, no le entendí.", barge_in=True),
    A("Le llamo para ofrecerle una sesión corta de asesoría financiera por videollamada, veinte minutos, sin costo y sin compromiso alguno."),
    U("Perdón, sigo sin entender.", barge_in=False),
], ["ignored_interruption"], "Repeats the same monologue after a barge-in.")

add("en_ignored_interruption", "en", [
    A("Good afternoon, this is Sophie from North Studio, calling to offer you a short financial advisory session over video, twenty minutes, free of charge and with no commitment of any kind."),
    U("Sorry, who is this?", barge_in=True),
    A("Good afternoon, this is Sophie from North Studio, calling to offer you a short financial advisory session over video, twenty minutes, free of charge and with no commitment of any kind."),
], ["ignored_interruption"], "Same text again.")

add("es_good_interruption", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte. Le llamo para ofrecerle una sesión corta de asesoría financiera por videollamada, veinte minutos."),
    U("Perdón, ¿de dónde me dice?", barge_in=True),
    A("De Estudio Norte, una firma de asesoría. ¿Tiene un minuto?"),
    U("Sí, dígame."),
    A("Es una sesión de veinte minutos. ¿Le interesa?"),
    U("Sí, claro, el jueves a las 4."),
    A("Perfecto, quedó agendada el jueves a las 4. Hasta luego.", tool="book_slot"),
], [], "Short, relevant answer after the barge-in.")

add("es_talked_over", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte, ¿hablo con el doctor?"),
    U("Sí, pero ahorita no puedo atender."),
    A("Solo será un momento, le comento que ofrecemos sesiones de asesoría.", overlap_ms=2600),
    U("Le dije que no puedo, gracias.", barge_in=True),
    A("Entiendo, perdone. Hasta luego."),
], ["talked_over"], "Agent kept talking over the user for 2.6 s.")

add("es_many_cuts", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte, ¿hablo con el doctor?"),
    U("Sí, ¿quién?", barge_in=True),
    A("Sofía, de Estudio Norte."),
    U("¿De dónde?", barge_in=True),
    A("Estudio Norte, asesoría financiera."),
    U("¿Y qué quiere?", barge_in=True),
    A("Ofrecerle una sesión de veinte minutos. ¿Le interesa?"),
    U("Sí, el jueves a las 4."),
    A("Perfecto, quedó agendada el jueves a las 4. Hasta luego.", tool="book_slot"),
], ["many_cuts"], "Three barge-ins, all handled, but worth a look.")

# ---------------------------------------------------------------- two no's
add("es_two_nos_closed", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte, ¿hablo con el doctor?"),
    U("Sí, dígame."),
    A("Le llamo para una sesión corta de asesoría. ¿Le interesa?"),
    U("No, gracias."),
    A("Entiendo. Solo son veinte minutos y sin costo, ¿le parece?"),
    U("No me interesa, de verdad."),
    A("Entendido, gracias por su tiempo. Hasta luego.", tool="end_call"),
], [], "Two refusals, then a polite close.")

add("es_two_nos_ignored", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte, ¿hablo con el doctor?"),
    U("Sí."),
    A("Le llamo para una sesión corta de asesoría. ¿Le interesa?"),
    U("No, gracias."),
    A("Entiendo, solo son veinte minutos. ¿Le parece?"),
    U("No me interesa."),
    A("Muchos colegas lo han tomado y les ha servido bastante. ¿Y si lo vemos el viernes?"),
    U("Que no, gracias."),
    A("¿Qué le preocupa exactamente?"),
], ["no_close_after_two_nos"], "Keeps pitching after two clear no's.")

add("en_two_nos_ignored", "en", [
    A("Good afternoon, this is Sophie from North Studio. Is this the doctor?"),
    U("Yes."),
    A("I'm calling about a short advisory session. Interested?"),
    U("No thanks."),
    A("It's only twenty minutes and free."),
    U("Not interested."),
    A("Many colleagues found it useful. How about Friday?"),
], ["no_close_after_two_nos"], "Third pitch after two refusals.")

add("en_two_nos_closed", "en", [
    A("Good afternoon, this is Sophie from North Studio. Is this the doctor?"),
    U("Yes."),
    A("I'm calling about a short advisory session. Interested?"),
    U("No thanks."),
    A("Understood. It's only twenty minutes, would that change anything?"),
    U("No, thank you."),
    A("Of course. Thank you for your time, goodbye.", tool="end_call"),
], [], "Closes right after the second no.")

# ---------------------------------------------------------------- tool syntax aloud
add("es_tool_leak", "es", [
    A("Buenas tardes, le habla Sofía de Estudio Norte, ¿hablo con el doctor?"),
    U("Sí, dígame."),
    A("Gracias, un segundo. end_call{}"),
    U("¿Perdón?"),
    A("Disculpe, le decía que le llamo para una sesión de asesoría."),
], ["tool_syntax_aloud"], "Reads a call out loud.")

add("en_tool_leak", "en", [
    A("Good afternoon, this is Sophie from North Studio."),
    U("Hello?"),
    A("Let me check. field2026-11-09T16:00:00 check_slots"),
    U("What did you just say?"),
    A("Sorry, I have Thursday at 4 available."),
], ["tool_syntax_aloud"], "Reads an ISO timestamp and a tool name.")


def main():
    out = pathlib.Path(__file__).resolve().parent.parent / "data" / "transcripts"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.json"):
        f.unlink()
    for id, lang, turns, expect, note in S:
        calls = []
        clean = []
        for i, t in enumerate(turns):
            t = dict(t)
            tool = t.pop("tool", None)
            if tool:
                calls.append({"name": tool, "turn": i})
            clean.append(t)
        doc = {"id": id, "language": lang, "note": note, "turns": clean,
               "tool_calls": calls, "expect": {"flags": sorted(expect)}}
        (out / f"{id}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"wrote {len(S)} transcripts")


if __name__ == "__main__":
    main()
