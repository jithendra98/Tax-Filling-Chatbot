from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configure Gemini AI
GOOGLE_API_KEY = "AIzaSyD5OQN6WyjdKyL_FuULQrUOF179APK1Smo"  # Replace with your Gemini API key
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

class TaxChatbot:
    def __init__(self):
        self.user_data = {"income": 0, "expenses": 0, "status": None,
                         "member1_name": "", "member1_regno": "",
                         "member2_name": "", "member2_regno": ""}
        self.standard_deductions = {"single": 13000, "married": 26000, "other": 13000}
        self.tax_brackets = [
            {"min": 0, "max": 12000, "rate": 0.10},
            {"min": 12001, "max": 50000, "rate": 0.12},
            {"min": 50001, "max": 100000, "rate": 0.22},
            {"min": 100001, "max": float("inf"), "rate": 0.32}
        ]
        self.step = "income"
        self.chat_history = []

    def calculate_tax(self):
        deduction = self.standard_deductions[self.user_data["status"]]
        taxable_income = max(0, self.user_data["income"] - self.user_data["expenses"] - deduction)
        tax = 0
        remaining_income = taxable_income
        for bracket in self.tax_brackets:
            if remaining_income <= 0:
                break
            taxable_in_bracket = min(remaining_income, bracket["max"] - bracket["min"])
            tax += taxable_in_bracket * bracket["rate"]
            remaining_income -= taxable_in_bracket
        return taxable_income, tax

    def get_gemini_response(self, prompt):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}. Fallback: {prompt}"

bot = TaxChatbot()

@app.route("/", methods=["GET"])
def index():
    if not bot.chat_history:
        initial_message = bot.get_gemini_response("Warmly greet and ask for 2025 income.")
        bot.chat_history.append({"sender": "bot", "text": initial_message})
    return render_template("index.html", chat_history=bot.chat_history)

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.form["user_input"]
    bot.user_data["member1_name"] = request.form.get("member1_name", "")
    bot.user_data["member1_regno"] = request.form.get("member1_regno", "")
    bot.user_data["member2_name"] = request.form.get("member2_name", "")
    bot.user_data["member2_regno"] = request.form.get("member2_regno", "")

    bot.chat_history.append({"sender": "user", "text": user_input})

    if bot.step == "income":
        try:
            bot.user_data["income"] = float(user_input)
            message = bot.get_gemini_response("Ask for deductible expenses in a friendly way.")
            bot.step = "expenses"
        except ValueError:
            message = bot.get_gemini_response("Kindly ask for a valid income number.")
    elif bot.step == "expenses":
        try:
            bot.user_data["expenses"] = float(user_input)
            message = bot.get_gemini_response("Cheerfully ask if they’re filing as single, married, or other.")
            bot.step = "status"
        except ValueError:
            message = bot.get_gemini_response("Gently request a valid expense amount.")
    elif bot.step == "status":
        if user_input.lower() in ["single", "married", "other"]:
            bot.user_data["status"] = user_input.lower()
            taxable_income, tax = bot.calculate_tax()
            summary = (f"Team: {bot.user_data['member1_name']} (Reg: {bot.user_data['member1_regno']}), "
                      f"{bot.user_data['member2_name']} (Reg: {bot.user_data['member2_regno']})<br>"
                      f"Income: ${bot.user_data['income']:.2f}<br>"
                      f"Expenses: ${bot.user_data['expenses']:.2f}<br>"
                      f"Standard Deduction: ${bot.standard_deductions[bot.user_data['status']]:.2f}<br>"
                      f"Taxable Income: ${taxable_income:.2f}<br>"
                      f"Estimated Tax: ${tax:.2f}<br>"
                      "File with Form 1040 at irs.gov!")
            message = bot.get_gemini_response(f"Present this tax summary clearly: {summary}")
            bot.step = "done"
        else:
            message = bot.get_gemini_response("Politely ask to choose single, married, or other.")

    bot.chat_history.append({"sender": "bot", "text": message})
    return jsonify({"chat_history": bot.chat_history})

if __name__ == "__main__":
    app.run(debug=True)