from pydantic import (
    BaseModel,
    EmailStr,
    AnyUrl,
    Field,
    field_validator,
    model_validator,
    computed_field,
)
from typing import List, Dict, Optional, Annotated


# 1. NESTED MODELS: We define smaller models first so they can be reused inside larger ones.
class Address(BaseModel):
    city: str
    state: str
    pin: str


class Patient(BaseModel):
    # 2. ANNOTATED & FIELD: The modern way to add extra validation and OpenAPI/Swagger documentation.
    name: Annotated[
        str,
        Field(
            max_length=50,
            title="Name of the patient",
            description="Give the name of the patient in less than 50 chars",
            examples=["Shree", "Koshti"],
        ),
    ]
    email: EmailStr  # Automatically checks for valid format (e.g., user@domain.com)
    linkedin_url: AnyUrl  # Automatically ensures this is a valid web address

    # 3. FIELD CONSTRAINTS: 'gt' = greater than, 'lt' = less than
    age: int = Field(gt=0, lt=120)

    # strict=True means Pydantic will NOT auto-convert an integer like 75 to 75.0. It MUST be a float.
    weight: Annotated[float, Field(gt=0, strict=True)]
    height: float

    married: Annotated[
        bool, Field(default=None, description="Is the patient married or not")
    ]

    # 4. OPTIONAL LISTS: This can be a list of strings, or it can be completely left out (None).
    allergies: Annotated[Optional[List[str]], Field(default=None, max_length=5)]
    contact_details: Dict[str, str]

    # 5. USING NESTED MODELS: We use the Address model we created at the top.
    address: Address

    # 6. CUSTOM DATA VALIDATION (Single Fields)
    # Checks the email value BEFORE the object is fully created (which is why we use @classmethod)
    @field_validator("email")
    @classmethod
    def email_validator(cls, value):
        valid_domains = ["hdfc.com", "icici.com"]
        domain_name = value.split("@")[-1]
        if domain_name not in valid_domains:
            raise ValueError("Not a valid domain")
        return value

    # Validators can also TRANSFORM data. This forces all names to be UPPERCASE automatically.
    @field_validator("name")
    @classmethod
    def transform_name(cls, value):
        return value.upper()

    # mode="after" means Pydantic does its standard type checking first, THEN runs your custom logic.
    @field_validator("age", mode="after")
    @classmethod
    def validate_age(cls, value):
        if 0 < value < 100:
            return value
        else:
            raise ValueError("Age should be in between 0 and 100")

    # 7. BUSINESS LOGIC (Multiple Fields)
    # @model_validator checks the ENTIRE model at once. Useful when one field depends on another.
    @model_validator(mode="after")
    def validate_emergency_contact(cls, model):
        # Here we check 'age' and 'contact_details' together
        if model.age > 60 and "emergency" not in model.contact_details:
            raise ValueError("Patients older than 60 must have an emergency contact")
        return model

    # 8. COMPUTED FIELDS
    # This acts like a normal database column, but it calculates itself automatically based on other fields!
    @computed_field
    @property
    def bmi(self) -> float:
        bmi = round(self.weight / (self.height**2), 2)
        return bmi


# --- MOCK DATABASE FUNCTIONS ---
def insert_patient_data(patient: Patient):
    print(patient.name)
    print(patient.age)
    print("inserted ...")


def update_patient_data(patient: Patient):
    print(f"\nPATIENT DATA => ")
    print(patient.name)
    print(patient.age)
    print(patient.allergies)
    print(patient.married)
    print(
        f"BMI {patient.bmi}"
    )  # Accessing the computed field just like a normal variable
    print("updated ...")


# --- EXECUTION ---

# 9. INSTANTIATING THE NESTED MODEL
address_dict = {"city": "pune", "state": "maharastra", "pin": "123546"}
address1 = Address(**address_dict)  # Using ** to unpack the dictionary!

patient_info = {
    "name": "shree",
    "email": "abc@hdfc.com",
    "linkedin_url": "http://linkedin.com/",
    "age": 61,
    "weight": 75.2,  # KG
    "height": 1.72,  # Mtr
    "married": False,
    "allergies": ["pollen", "dust"],
    "contact_details": {"phone": "258147369", "emergency": "369258147"},
    "address": address1,  # Passing the Address object we just created
}

# 10. INSTANTIATING THE MAIN MODEL
patient1 = Patient(
    **patient_info
)  # Unpacking the main dictionary. This triggers ALL the validators above.

update_patient_data(patient1)

print("\nADDRESS DATA => ")
# 11. DOT NOTATION: Accessing nested data easily
print(f"City => {patient1.address.city}")
print(f"State => {patient1.address.state}")
print(f"Pincode => {patient1.address.pin}")

# 12. SERIALIZATION
# Converts the Pydantic Python Object back into a standard Python Dictionary (ready to be sent as JSON)
# exclude_unset=True means it won't include fields that were never provided (keeps the output clean)
temp = patient1.model_dump(exclude_unset=True)

print(temp)
print(type(temp))
