from fastapi import FastAPI, Path, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional
import json

app = FastAPI()

# --- PYDANTIC MODELS ---


# Main model for creating and validating new patients
class Patient(BaseModel):
    id: Annotated[str, Field(..., description="ID of the patient", examples=["P001"])]
    name: Annotated[str, Field(..., description="Name of the patient")]
    city: Annotated[str, Field(..., description="City where the patient is living")]
    age: Annotated[int, Field(..., gt=0, le=120, description="Age of the patient")]
    gender: Annotated[
        Literal["male", "female", "others"],
        Field(..., description="Gender of the patient"),
    ]
    height: Annotated[float, Field(..., gt=0, description="Height of the patient")]
    weight: Annotated[float, Field(..., gt=0, description="Weight of the patient")]

    # Automatically calculates BMI when a Patient object is created
    @computed_field
    @property
    def bmi(self) -> float:
        bmi = round(self.weight / (self.height**2), 2)
        return bmi

    # Automatically calculates health verdict based on the computed BMI
    @computed_field
    @property
    def verdict(self) -> float:
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25:
            return "Normal"
        elif self.bmi < 30:
            return "Normal"
        else:
            return "Obese"


# Schema specifically for updating patients (all fields are Optional)
class PatientUpdate(BaseModel):
    name: Annotated[Optional[str], Field(default=None)]
    city: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int], Field(default=None, gt=0)]
    gender: Annotated[Optional[Literal["male", "Female"]], Field(default=None)]
    height: Annotated[Optional[float], Field(default=None, gt=0)]
    weight: Annotated[Optional[float], Field(default=None, gt=0)]


# --- DATABASE HELPERS ---


def load_data():
    """Reads and parses the JSON file into a Python dictionary."""
    with open(f"patients.json", "r") as f:
        data = json.load(f)
    return data


def save_data(data):
    """Writes the Python dictionary back to the JSON file."""
    with open(f"patients.json", "w") as f:
        json.dump(data, f)


# --- API ENDPOINTS ---


@app.get("/")
def hello():
    return {"message": "Hello World"}


@app.get("/about")
def about():
    return {"message": "A fully functional API to manage your patient records"}


# READ ALL
@app.get("/view")
def view():
    data = load_data()
    return data


# READ SINGLE (Extracts patient_id from the URL path)
@app.get("/patient/{patient_id}")
def view_patient(
    patient_id: str = Path(
        ...,
        description="ID of the patient in the DB",
        examples="P001",
    )
):
    data = load_data()

    if patient_id in data:
        return data[patient_id]

    raise HTTPException(status_code=404, detail="Patient not found")


# SORT (Uses URL query parameters like /sort?sort_by=height&order=desc)
@app.get("/sort")
def sort_patients(
    sort_by: str = Query(..., description="Sort on the basis of height, weight or bmi"),
    order: str = Query("asc", description="Sort in asc or desc order"),
):
    valid_fields = ["height", "weight", "bmi"]

    if sort_by not in valid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field select from {valid_fields}",
        )

    if order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400, detail="Invalid order select between asc and desc"
        )

    data = load_data()

    # Convert dictionary values to a list and sort based on the chosen key
    sort_order = True if order == "desc" else False
    sorted_data = sorted(
        data.values(),
        key=lambda x: x.get(sort_by, 0),
        reverse=sort_order,
    )

    return sorted_data


# CREATE (Expects the full Patient JSON in the request body)
@app.post("/create")
def create_patient(patient: Patient):  # Pydantic validates incoming data automatically
    data = load_data()

    # Prevent duplicate IDs
    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient already exists")

    # Convert the valid Pydantic object to a dict, removing the 'id' field
    data[patient.id] = patient.model_dump(exclude=["id"])

    save_data(data)

    return JSONResponse(
        status_code=201, content={"message": "Patient created successfully"}
    )


# UPDATE (Allows partial updates using PatientUpdate schema)
@app.put("/edit/{patient_id}")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    data = load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing_patient_info = data[patient_id]

    # exclude_unset=True ensures we ONLY get the fields the user actually sent
    updated_patient_info = patient_update.model_dump(exclude_unset=True)

    # Overwrite old values with the newly provided ones
    for key, value in updated_patient_info.items():
        existing_patient_info[key] = value

    # Re-instantiate the main Patient model to recalculate BMI and verdict
    existing_patient_info["id"] = patient_id
    patient_pydantic_obj = Patient(**existing_patient_info)

    # Dump back to dict (excluding ID) to match database structure
    final_patient_data = patient_pydantic_obj.model_dump(exclude=["id"])

    data[patient_id] = final_patient_data

    save_data(data)

    return JSONResponse(status_code=200, content={"message": "patient updated"})


# DELETE
@app.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):
    data = load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Remove the patient key from the dictionary
    del data[patient_id]

    save_data(data)

    return JSONResponse(status_code=200, content={"message": "patient deleted"})
