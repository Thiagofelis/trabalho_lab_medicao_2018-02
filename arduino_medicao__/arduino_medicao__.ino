const int ledPin = 13;
volatile byte state = LOW;
unsigned int j = 2;
unsigned long t1;
unsigned int low_buffer, high_buffer;
unsigned char incomingByte;
 
void setup() {

   // 34,5 kHz
   Serial.begin(345600);   // !! 115200, 230400, 345600,   460800 X


   // TIMER0: pre-scaler = 64, ctc, 8.9khz
   TCCR0A = 0x02; // CTC mode
   TCCR0B = 0x03; // pre-scaler 64
   OCR0A = 27; // == 28
   TIMSK0 = 0x00;

   PRR &= 0b11111110; // PRADC = 0  

   SREG |= 0b10000000; // global interrupts enabled

   // ADC: 
   ADMUX = 0b01000000;//tensao de referencia selecao do canal igual a 0 
   ADCSRB = (ADCSRB & 0b11111000) | 0b00000011; // configura trigger
   ADCSRA = (ADCSRA & 0b00010000) | 0b10101111; //flag de interrupção pre-scalar do ADC = 128 interrupt enable  auto trigger e adc enable (flatou só o start)
   
}
 
void loop() {

   if (Serial.available() > 0) {

      incomingByte = Serial.read();
      if (incomingByte == 0xe6)
      {
         TIMSK0 = 0x02; // comeca a transmitir
      }
   }

}

ISR (ADC_vect)
{
   low_buffer = ADCL;
   high_buffer = ADCH;
}

// order: 0 1 2 0 1 3 0 1 4
 
ISR(TIMER0_COMPA_vect)
{
   if ((ADMUX & 0b00000111) == 0x00) // amostrando canal 0, acabou de amostrar canal 2, 3 ou 4
   {
      if (j == 0)
       {
         Serial.write(high_buffer | 0b10100000);  //0x10100000 + (j << 4)
         Serial.write(low_buffer);
         j = 1;
      } 
      else
      {
        if (j == 1)
        {
           Serial.write(high_buffer | 0b10110000);
           Serial.write(low_buffer);
           j = 2;
        }
        else // j = 2
        {
           Serial.write(high_buffer | 0b11000000);
           Serial.write(low_buffer);
           j = 0;
        }
      }
      ADMUX = (ADMUX & 0b11111000) | 0b00000001; // proxima amostragem no canal 1
   }
   else
   {
      if((ADMUX & 0b00000111) == 0x01) // amostrando canal 1, acabou de amostrar o canal 0
      {
         Serial.write(high_buffer | 0b10000000);
         Serial.write(low_buffer);
         ADMUX = (ADMUX & 0b11111000) | (j + 2); // proxima amostragem no canal j + 2
      }
      else // amostrando canal 2, 3 ou 4, acabou de amostrar o canal 1
      {
         Serial.write(high_buffer | 0b10010000);
         Serial.write(low_buffer);
         ADMUX = (ADMUX & 0b11111000) | 0x0; // proxima amostragem no canal 0
      }   
   }
}
